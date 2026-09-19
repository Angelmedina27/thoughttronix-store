MAP:

<b>1. The apps and what each owns.<b> This project has four different maps. These maps are accounts, products, orders, and dashboard. The Accounts section takes care of user profiles and logins. The Products section holds the store catalog items. The Orders section manages the shopping carts for checkout and buying items. Lastly the dashboard section is for the staff backend pages.

<b>2. The path of one request.<b> When someone visits the home page, the request goes through "config/urls.py" which then passes it off to "products/urls.py". Next, a class view that is named "CatalogView" which stays inside "products/views.py" grabs the product data from the database and displays it on the screen using the "templates/products/catalog.html" template.

<b>3. A model you read.<b> I decided to look at the Cart model in "orders/models.py", which links a shopping cart to a specific user. Something new to me was the "for_user" method.

<b>4. Deleting a category. <b> When a Category is deleted, the "on_delete" setting on the ForeignKey field decides what happens to that specific product whether it be to block the delete or cascade it.

<b>5. Where the tests live.<b> The test files are located right inside the folders next to the regular code files they are checking. The "conftest.py" file at the root holds setup fixtures and prodives tests that you can reuse so you don't have to keep coding them over and over again manually.

<b>6. One thing you're still working to understand.<b> I think the thing I am still working to understand is how testing fixtures work in pytest compared to a normal Django TestCase.A