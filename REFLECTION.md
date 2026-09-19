## Featured Products

<b>1. Trace the feature.<b> When you check the featured box for a product, it changes the "is_featured" column in the database from False to True. When a user loads up the storefront website, the code inside "products/views.py" calls the database to pull all the store products along with that true/false check. Then, the template files "catalog.html" and "detail.html" use an "{% if product.is_featured %}" tag to spot that it is True and render the "featured" badge on the storefront.

<b>2. How you verified it.<b> I checked that my code worked by launching the web store in the browser. I went to the home catalog page and searched for the 3 specific products and checked to make sure that the items we updated had the "feature" badge displaged.

<b>3. Judgement.<b> It was a little tricky making sure the featured badge only showed up on the products we picked instead of every product on the site. To fix it I asked Claude for assistance and it was able to force the "is_featured" value to make the feature show up correctly.