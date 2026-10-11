## Discount Coupons

<b>1. One decision from grill me.</b> One question that the agent asked from grill me was "Where should 'one use per customer' be enforced, given customers can check out as guests?". The agent recommened the decision "Per logged-in account only" which I agreed heavily with due to the fact that if we made it open to guest accounts, it would allow one person to use the code multiple times just using guest accounts which most likely would need an email adress.

<b>2. The change.</b> After reviewing the features, I wanted to change the message that displayed from an invalid coupon since I felt the original message "That code has expired." wasn't enough help for the customers. I began by changing the message to say "Oops! That discount code is invalid or has reached its usage limit." but the test failed. It failed because the test required the word "expired" to be within the message, so I went back into the file and replaced "invalid" with "expired" so the message could read "Oops! That discount code is expired or has reached its usage limit." and once I changed that, all the tests passed.

## Featured Products

<b>1. Trace the feature.</b> When you check the featured box for a product, it changes the "is_featured" column in the database from False to True. When a user loads up the storefront website, the code inside "products/views.py" calls the database to pull all the store products along with that true/false check. Then, the template files "catalog.html" and "detail.html" use an "{% if product.is_featured %}" tag to spot that it is True and render the "featured" badge on the storefront.

<b>2. How you verified it.</b> I checked that my code worked by launching the web store in the browser. I went to the home catalog page and searched for the 3 specific products and checked to make sure that the items we updated had the "feature" badge displaged.

<b>3. Judgement.</b> It was a little tricky making sure the featured badge only showed up on the products we picked instead of every product on the site. To fix it I asked Claude for assistance and it was able to force the "is_featured" value to make the feature show up correctly.

## Product Images

<b>1. One decision from grill me.</b> Grill-me recommended using standard Django validators for file-constraints such as what file types are allowed in relation to the images. I realized that if an employee uploads an invalid file type like a text file, which one was included in the 13 images that came from the download file on the assignment, it would cause an error. Because of this I decided to tell the agent to create a sort of filter to allow it to catch wrong file extensions and display a message of "Allowed extensions are: png, jpg, jpeg, webp."

<b>2. Find the upload code.</b>  Filename- models.py Line number- 80-84 under the products folder. Line of code- "image = models.ImageField(
        upload_to="products/",
        blank=True,
        validators=[validate_image_extension],
    )" The "upload to" value tells Django to automatically create a subfolder named products/ inside our media folder and store any uploaded files in that location.
<b>3. Follow the upload process.</b> 1. It is stored at media/products/ambientrest.png. 2. Line of code- "image = models.ImageField(
        upload_to="products/",
        blank=True,
        validators=[validate_image_extension],
    )" 3. The browser requests http://127.0.0.1:8000/media/products/ambientrest.png.jpg to load the image on screen.

## Account Security Center

<b>1. Review one phase</b> The phase I am choosing is phase 6, which added brute-force sign-in lockout features. By the end of the phase the working behavior that was supposed to exist was that a user gets locked-out after 5 failed login attempts. I verified it by going to the login page and and using the customer login credentials and using an incorrect password 5 times in a row. The 6th try is where the page fully blocked me from any more attempts and showed a red error message saying "Too many attempts – try again in 15 minutes.". It worked perfectly on the first try and since it did lock-out even the admin from the both the storefront and the admin page, that showed me the evidence I needed to approve it.

<b>2. Authentication code versus the lesson.</b> The first component is the "SignupForm" which is located in the "accounts/forms.py". The line of code is "class SignupForm(UserCreationForm):". This component provides the form boxes that users type their information into to register. The implementation of this component matches the authentication pattern from the lesson because the lesson points out that Django's stock form leaves out the email field box entirely. This component basically forces the form to include email registration so all users have an email for account recorvery purposes and such. The second component is the "SignOutView" which is located in the "accounts/views.py". The line of code is "class SignOutView(LogoutView):". This component is what allows the user to log out of their account securly. The implementation of this matches the authentication pattern from the lesson as the lesson shows that logging out inherits directly from Django's built-in "LogoutView" then it displays an informational text note saying "You have signed out.".

<b>3. Password management versus the lesson.</b> I choose password change which is located in the "accounts/views.py". The component is uses is "ChangePasswordView". This component checks if you know your current password before letting you change to a new one. It's implementation compares with the pattern from the lesson because it inherits directly from Django's built-in "PasswordChangeView" to securely begin the change while "PasswordChangeDoneView" finishes it.

<b>4. The tracer-bullet plan. </b> I chose phase 2 as it was a useful stopping point because at the end of that phase a signed in user could navigate to the "Account Security" section under their account to see their information displayed such as their email address. Having this working behavior early on made the feature easier to review because we could visually see that our navigation links, views, and template layouts worked on the actual webpage.