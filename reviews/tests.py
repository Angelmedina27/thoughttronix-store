"""Reviews: eligibility, the model's rules, the form, and writing a review."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from conftest import make_order
from orders.models import Order
from products.models import Product

from .forms import ReviewForm
from .models import Review

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


def write_url(product):
    return reverse("reviews:write", kwargs={"slug": product.slug})


# --- Eligibility -------------------------------------------------------------


def test_a_customer_with_a_delivered_order_may_review(
    delivered_order, customer, product
):
    assert Review.objects.can_create(customer, product)


@pytest.mark.parametrize(
    "status",
    [Order.Status.PLACED, Order.Status.SHIPPED, Order.Status.CANCELLED],
)
def test_an_undelivered_order_is_not_enough(customer, product, status):
    make_order(customer, product, status)

    assert not Review.objects.can_create(customer, product)


def test_no_order_means_no_review(customer, product):
    assert not Review.objects.can_create(customer, product)


def test_a_delivered_order_of_another_product_is_not_enough(
    customer, product, category
):
    other = Product.objects.create(
        name="Calm Collar",
        slug="calm-collar",
        price=Decimal("59.00"),
        category=category,
    )
    make_order(customer, other, Order.Status.DELIVERED)

    assert not Review.objects.can_create(customer, product)


def test_staff_never_review_even_with_a_delivered_order(staff_user, product):
    make_order(staff_user, product, Order.Status.DELIVERED)

    assert not Review.objects.can_create(staff_user, product)


def test_anonymous_users_cannot_review(product):
    assert not Review.objects.can_create(AnonymousUser(), product)


def test_an_existing_review_ends_eligibility(review, customer, product):
    assert not Review.objects.can_create(customer, product)


# --- Model -------------------------------------------------------------------


def test_one_review_per_customer_per_product(review, customer, product):
    with pytest.raises(IntegrityError):
        Review.objects.create(
            user=customer, product=product, rating=5, comment="A second opinion."
        )


@pytest.mark.parametrize("rating", [0, 6])
def test_ratings_outside_1_to_5_are_rejected(customer, product, rating):
    review = Review(user=customer, product=product, rating=rating, comment="x" * 20)

    with pytest.raises(ValidationError):
        review.full_clean()


def test_deleting_the_product_deletes_its_reviews(review, product):
    product.delete()

    assert not Review.objects.exists()


def test_deleting_the_user_deletes_their_reviews(review, customer):
    customer.delete()

    assert not Review.objects.exists()


def test_visible_excludes_hidden_reviews(review, other_customer, product):
    hidden = Review.objects.create(
        user=other_customer,
        product=product,
        rating=1,
        comment="Spam spam spam spam spam.",
        is_hidden=True,
    )

    visible = Review.objects.visible()

    assert review in visible
    assert hidden not in visible


def test_reviews_come_newest_first(review, other_customer, product):
    newer = Review.objects.create(
        user=other_customer,
        product=product,
        rating=5,
        comment="x" * 20,
        created_at=review.created_at + timedelta(minutes=1),
    )

    assert list(Review.objects.all()) == [newer, review]


@pytest.mark.parametrize(
    ("seconds_later", "edited"),
    [(0, False), (60, False), (61, True), (3600, True)],
)
def test_a_review_is_edited_only_when_saved_over_a_minute_later(
    review, seconds_later, edited
):
    review.updated_at = review.created_at + timedelta(seconds=seconds_later)

    assert review.edited is edited


# --- Form --------------------------------------------------------------------


def test_the_form_accepts_a_rating_and_a_real_comment():
    form = ReviewForm(data={"rating": "5", "comment": "Finished my sentences. 10/10."})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["rating"] == 5


@pytest.mark.parametrize(
    "comment",
    ["Too short.", "   Too short, padded.    ", " " * 40],
)
def test_comments_under_20_characters_are_rejected(comment):
    form = ReviewForm(data={"rating": "4", "comment": comment})

    assert not form.is_valid()
    assert "comment" in form.errors


def test_the_short_comment_error_is_friendly():
    form = ReviewForm(data={"rating": "4", "comment": "Meh."})

    form.is_valid()

    assert "at least 20 characters" in form.errors["comment"][0]


@pytest.mark.parametrize("rating", ["0", "6", "", "five"])
def test_out_of_range_ratings_are_rejected(rating):
    form = ReviewForm(data={"rating": rating, "comment": "x" * 30})

    assert not form.is_valid()
    assert "rating" in form.errors


# --- Writing a review --------------------------------------------------------


def test_an_eligible_customer_sees_the_form(client, delivered_order, customer, product):
    client.force_login(customer)

    response = client.get(write_url(product))

    assert response.status_code == HTTPStatus.OK
    assert "Post review" in response.content.decode()


def test_posting_a_review_redirects_to_the_product_with_a_message(
    client, delivered_order, customer, product
):
    client.force_login(customer)

    response = client.post(
        write_url(product),
        {"rating": "5", "comment": "  It knew my coffee order before I did.  "},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == product.get_absolute_url()
    assert "your review is live" in response.content.decode()
    review = Review.objects.get()
    assert (review.user, review.product, review.rating) == (customer, product, 5)
    assert review.comment == "It knew my coffee order before I did."


def test_an_invalid_review_rerenders_the_form(
    client, delivered_order, customer, product
):
    client.force_login(customer)

    response = client.post(write_url(product), {"rating": "5", "comment": "Short."})

    assert response.status_code == HTTPStatus.OK
    assert "at least 20 characters" in response.content.decode()
    assert not Review.objects.exists()


def test_anonymous_users_are_sent_to_sign_in(client, product):
    response = client.get(write_url(product))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.parametrize("method", ["get", "post"])
def test_ineligible_customers_get_403(client, customer, product, method):
    make_order(customer, product, Order.Status.SHIPPED)
    client.force_login(customer)

    response = getattr(client, method)(
        write_url(product), {"rating": "5", "comment": "x" * 30}
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not Review.objects.exists()


def test_staff_get_403(client, staff_user, product):
    make_order(staff_user, product, Order.Status.DELIVERED)
    client.force_login(staff_user)

    assert client.get(write_url(product)).status_code == HTTPStatus.FORBIDDEN


def test_an_unknown_product_is_404(client, customer):
    client.force_login(customer)

    response = client.get(reverse("reviews:write", kwargs={"slug": "no-such-thing"}))

    assert response.status_code == HTTPStatus.NOT_FOUND


# --- Editing a review --------------------------------------------------------


def test_saving_an_existing_review_updates_it_in_place(
    client, review, customer, product
):
    client.force_login(customer)

    response = client.post(
        write_url(product),
        {"rating": "2", "comment": "Six months in, it started finishing my sentences."},
        follow=True,
    )

    assert response.redirect_chain == [(product.get_absolute_url(), HTTPStatus.FOUND)]
    assert "your review is updated" in response.content.decode()
    updated = Review.objects.get()
    assert updated.pk == review.pk
    assert updated.rating == 2
    assert updated.comment == "Six months in, it started finishing my sentences."


def test_editing_still_works_after_the_order_is_cancelled(
    client, review, delivered_order, customer, product
):
    delivered_order.status = Order.Status.CANCELLED
    delivered_order.save()
    client.force_login(customer)

    response = client.post(
        write_url(product),
        {"rating": "1", "comment": "Refunded, but I stand by every word of this."},
    )

    assert response.status_code == HTTPStatus.FOUND
    review.refresh_from_db()
    assert review.rating == 1
    assert review.comment == "Refunded, but I stand by every word of this."


def test_an_existing_review_opens_in_the_edit_form_prefilled(
    client, review, customer, product
):
    client.force_login(customer)

    response = client.get(write_url(product))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "Edit your review" in content
    assert "Save changes" in content
    assert "Post review" not in content
    assert response.context["form"].instance == review
    assert review.comment in content


# --- The product page --------------------------------------------------------


def test_the_product_page_shows_reviews_newest_first(
    client, review, other_customer, product
):
    newer = Review.objects.create(
        user=other_customer,
        product=product,
        rating=2,
        comment="Listened a little too well, honestly.",
        created_at=review.created_at + timedelta(minutes=1),
    )

    content = client.get(product.get_absolute_url()).content.decode()

    assert content.index("Listened a little too well") < content.index(
        "Knew what I wanted"
    )
    assert newer.user.username in content
    assert review.created_at.strftime("%b") in content


def test_the_product_page_shows_the_average_and_count(
    client, review, other_customer, product
):
    Review.objects.create(
        user=other_customer, product=product, rating=1, comment="x" * 20
    )

    content = client.get(product.get_absolute_url()).content.decode()

    assert "★ 2.5" in content
    assert "based on 2 reviews" in content


def test_hidden_reviews_stay_off_the_product_page(client, review, product):
    review.is_hidden = True
    review.save()

    content = client.get(product.get_absolute_url()).content.decode()

    assert "Knew what I wanted" not in content
    assert "No reviews yet" in content


def test_the_product_page_has_a_designed_empty_state(client, product):
    content = client.get(product.get_absolute_url()).content.decode()

    assert "No reviews yet" in content
    assert "customers whose orders were delivered" in content


def test_eligible_customers_see_the_write_button(
    client, delivered_order, customer, product
):
    client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert "Write a review" in content
    assert write_url(product) in content


@pytest.mark.parametrize("status", [Order.Status.PLACED, Order.Status.SHIPPED])
def test_undelivered_customers_see_no_write_button(client, customer, product, status):
    make_order(customer, product, status)
    client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert "Write a review" not in content


def test_anonymous_shoppers_and_staff_see_no_write_button(client, staff_user, product):
    make_order(staff_user, product, Order.Status.DELIVERED)

    assert (
        "Write a review" not in client.get(product.get_absolute_url()).content.decode()
    )
    client.force_login(staff_user)
    assert (
        "Write a review" not in client.get(product.get_absolute_url()).content.decode()
    )


def test_a_customer_who_reviewed_sees_the_edit_button(
    client, review, customer, product
):
    client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert "Edit your review" in content
    assert "Write a review" not in content
    assert write_url(product) in content


def test_other_viewers_see_no_edit_button(client, review, other_customer, product):
    assert (
        "Edit your review"
        not in client.get(product.get_absolute_url()).content.decode()
    )
    client.force_login(other_customer)
    assert (
        "Edit your review"
        not in client.get(product.get_absolute_url()).content.decode()
    )


def test_edited_reviews_are_marked(client, review, product):
    Review.objects.filter(pk=review.pk).update(
        updated_at=review.created_at + timedelta(days=30)
    )

    assert "edited" in client.get(product.get_absolute_url()).content.decode()


def test_unedited_reviews_are_not_marked(client, review, product):
    assert "edited" not in client.get(product.get_absolute_url()).content.decode()


def test_the_viewers_own_review_is_pinned_first(
    client, review, customer, other_customer, product
):
    Review.objects.create(
        user=other_customer,
        product=product,
        rating=2,
        comment="Listened a little too well, honestly.",
        created_at=review.created_at + timedelta(minutes=1),
    )
    client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert content.index("Knew what I wanted") < content.index(
        "Listened a little too well"
    )
    assert "Your review" in content
    assert content.count("Knew what I wanted") == 1


# --- Deleting a review -------------------------------------------------------


def delete_url(review):
    return reverse("reviews:delete", kwargs={"pk": review.pk})


def test_confirming_a_delete_removes_the_review_and_returns_to_the_product(
    client, review, customer, product
):
    client.force_login(customer)

    response = client.post(delete_url(review), follow=True)

    assert response.redirect_chain == [(product.get_absolute_url(), HTTPStatus.FOUND)]
    assert "your review is deleted" in response.content.decode()
    assert not Review.objects.exists()


@pytest.mark.parametrize("method", ["get", "post"])
def test_deleting_someone_elses_review_is_forbidden(
    client, review, other_customer, method
):
    client.force_login(other_customer)

    response = getattr(client, method)(delete_url(review))

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert Review.objects.filter(pk=review.pk).exists()


def test_the_owner_sees_a_confirmation_page(client, review, customer, product):
    client.force_login(customer)

    response = client.get(delete_url(review))

    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert f"Delete your review of {product.name}?" in content
    assert review.comment in content
    assert Review.objects.filter(pk=review.pk).exists()


@pytest.mark.parametrize("method", ["get", "post"])
def test_anonymous_users_are_sent_to_sign_in_to_delete(client, review, method):
    response = getattr(client, method)(delete_url(review))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))
    assert Review.objects.filter(pk=review.pk).exists()


def test_an_unknown_review_is_404(client, customer):
    client.force_login(customer)

    response = client.get(reverse("reviews:delete", kwargs={"pk": 999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_after_deleting_the_customer_can_write_a_new_review(
    client, review, customer, product
):
    client.force_login(customer)
    client.post(delete_url(review))

    content = client.get(product.get_absolute_url()).content.decode()
    assert "Write a review" in content
    assert "Edit your review" not in content

    response = client.post(
        write_url(product),
        {"rating": "3", "comment": "Second thoughts, fully my own this time."},
    )

    assert response.status_code == HTTPStatus.FOUND
    new_review = Review.objects.get()
    assert new_review.pk != review.pk
    assert new_review.rating == 3


def test_the_author_sees_a_delete_link_on_their_review(
    client, review, customer, product
):
    client.force_login(customer)

    content = client.get(product.get_absolute_url()).content.decode()

    assert delete_url(review) in content


def test_other_viewers_see_no_delete_link(client, review, other_customer, product):
    assert (
        delete_url(review)
        not in client.get(product.get_absolute_url()).content.decode()
    )
    client.force_login(other_customer)
    assert (
        delete_url(review)
        not in client.get(product.get_absolute_url()).content.decode()
    )


# --- Ratings on catalog and category cards -----------------------------------


def test_with_ratings_annotates_visible_reviews_only(
    review, other_customer, product, unavailable_product
):
    Review.objects.create(
        user=other_customer, product=product, rating=5, comment="x" * 20
    )
    hidden_author = get_user_model().objects.create_user(username="spammer")
    Review.objects.create(
        user=hidden_author,
        product=product,
        rating=1,
        comment="Spam spam spam spam spam.",
        is_hidden=True,
    )

    rated = Product.objects.with_ratings().get(pk=product.pk)
    unrated = Product.objects.with_ratings().get(pk=unavailable_product.pk)

    assert rated.average_rating == 4.5
    assert rated.review_count == 2
    assert unrated.average_rating is None
    assert unrated.review_count == 0


def test_catalog_cards_show_the_rounded_average_or_no_reviews_yet(
    client, review, other_customer, product, unavailable_product
):
    Review.objects.create(
        user=other_customer, product=product, rating=5, comment="x" * 20
    )
    third = get_user_model().objects.create_user(username="third")
    Review.objects.create(user=third, product=product, rating=5, comment="x" * 20)

    content = client.get(reverse("products:catalog")).content.decode()

    assert "★ 4.7 (3)" in content
    assert content.count("No reviews yet") == 1


def catalog_query_count(client):
    with CaptureQueriesContext(connection) as queries:
        client.get(reverse("products:catalog"))
    return len(queries)


def test_the_catalog_query_count_does_not_grow_with_products(
    client, review, other_customer, product, category, tag
):
    product.tags.add(tag)
    baseline = catalog_query_count(client)

    for n in range(5):
        extra = Product.objects.create(
            name=f"Extra {n}", slug=f"extra-{n}", price=Decimal("10"), category=category
        )
        extra.tags.add(tag)
        Review.objects.create(
            user=other_customer, product=extra, rating=3, comment="x" * 20
        )

    assert catalog_query_count(client) == baseline


def test_category_pages_show_the_same_ratings(client, review, product, category):
    content = client.get(category.get_absolute_url()).content.decode()

    assert "★ 4.0 (1)" in content


def test_hidden_reviews_are_left_off_catalog_cards(client, review, product):
    review.is_hidden = True
    review.save()

    content = client.get(reverse("products:catalog")).content.decode()

    assert "★" not in content
    assert "No reviews yet" in content
