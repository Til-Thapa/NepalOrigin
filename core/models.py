from django.db import models

# Users
class UserRole(models.Model):
    role_id = models.AutoField(db_column='role_id', primary_key=True)
    role = models.CharField(db_column='role', max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = 'user_role'

    def __str__(self):
        return self.role


class User(models.Model):
    user_id = models.AutoField(db_column='user_id', primary_key=True)
    role_id = models.ForeignKey(UserRole, db_column='role_id', on_delete=models.SET_NULL, null=True, blank=True, default=1)
    first_name = models.CharField(db_column='first_name', max_length=100)
    middle_name = models.CharField(db_column='middle_name', max_length=100, null=True, blank=True)
    last_name = models.CharField(db_column='last_name', max_length=100)
    email = models.CharField(db_column='email', unique=True)
    password = models.CharField(db_column='password')
    image = models.ImageField(upload_to='profile_images/', db_column='image', null=True, blank=True)
    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        managed = False
        db_table = 'users'

    def save(self, *args, **kwargs):
        if not self.role_id:
            self.role_id = UserRole.objects.get(role_id=1)
        super(User, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class Business(models.Model):
    business_id = models.AutoField(db_column='business_id', primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')

    business_name = models.CharField(db_column='business_name', max_length=100)
    business_phone_number = models.CharField(db_column='business_phone_number', max_length=15, unique=True)
    status = models.CharField(db_column='status', max_length=50, default='Pending', choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Reapplied', 'Reapplied')])

    citizenship_front = models.ImageField(upload_to='citizenship/', db_column='citizenship_front', null=True, blank=True)
    citizenship_back = models.ImageField(upload_to='citizenship/', db_column='citizenship_back', null=True, blank=True)

    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        managed = False
        db_table = 'business'

    def __str__(self):
        return f"{self.business_name} {self.user_id.first_name}"



class ProductCategory(models.Model):
    category_id = models.AutoField(db_column='category_id', primary_key=True)
    category_name = models.CharField(db_column='category_name', max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = 'product_category'

    def __str__(self):
        return self.category_name


class Product(models.Model):
    product_id = models.AutoField(db_column='product_id', primary_key=True)
    business_id = models.ForeignKey(Business, db_column='business_id', on_delete=models.SET_NULL, null=True, blank=True)
    category_id = models.ForeignKey(ProductCategory, db_column='category_id', on_delete=models.SET_NULL, null=True, blank=True)

    product_name = models.CharField(db_column='product_name', max_length=100)
    product_img = models.ImageField(upload_to='product_img/', db_column='product_img', null=True, blank=True)
    product_description = models.TextField(db_column='product_description', max_length=100)
    price = models.DecimalField(db_column='price', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(db_column='quantity')

    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        managed = False
        db_table = 'product'

    def __str__(self):
        return f"{self.business_id} {self.product_name}"


class Review(models.Model):
    review_id = models.AutoField(db_column='review_id', primary_key=True)
    product_id = models.ForeignKey(Product, db_column='product_id', on_delete=models.CASCADE, null=True, blank=True)
    user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.CASCADE, null=True, blank=True)
    comment = models.TextField(db_column='comment')
    rating = models.IntegerField(db_column='rating',default=1)
    created_at = models.DateTimeField(db_column='created_at',auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'review'

    def __str__(self):
        return f"Review for {self.product_id.product_name} by {self.user_id.first_name}"


class Cart(models.Model):
    cart_id = models.AutoField(db_column='cart_id', primary_key=True)
    user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        db_table = 'cart'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart({self.user_id.email if self.user_id else 'Guest'})"


class CartItem(models.Model):
    cart_item_id = models.AutoField(db_column='cart_item_id', primary_key=True)
    cart_id = models.ForeignKey(Cart, db_column='cart_id', related_name='items', on_delete=models.CASCADE)
    product_id = models.ForeignKey(Product, db_column='product_id', on_delete=models.SET_NULL, null=True, blank=True)

    quantity = models.PositiveIntegerField(db_column='quantity', default=1)
    price = models.DecimalField(db_column='price', max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(db_column='subtotal', max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        db_table = 'cart_item'
        unique_together = ('cart_id', 'product_id')

    def __str__(self):
        return f"CartItem({self.cart_id}) - {self.product_id.product_name} x {self.quantity}"

class Orders(models.Model):
    order_id = models.AutoField(db_column='order_id', primary_key=True)
    user_id = models.ForeignKey(User, db_column='user_id', on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(db_column='full_name', max_length=100)
    phone_number = models.CharField(db_column='phone_number', max_length=20)
    address_line1 = models.CharField(db_column='address_line1', max_length=255)
    address_line2 = models.CharField(db_column='address_line2', max_length=255, blank=True, null=True)
    city = models.CharField(db_column='city', max_length=100)

    created_at = models.DateTimeField(db_column='created_at', auto_now_add=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True)

    class Meta:
        managed = False
        db_table = 'orders'

    def __str__(self):
        return f"{self.full_name} {self.order_id}"


class Order_Item(models.Model):
    order_item_id = models.AutoField(db_column='order_item_id', primary_key=True)
    order_id = models.ForeignKey(Orders, db_column='order_id', on_delete=models.SET_NULL, null=True, blank=True)

    product_id = models.ForeignKey(Product, db_column='product_id', on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(db_column='price', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(db_column='quantity')
    subtotal = models.DecimalField(db_column='subtotal', max_digits=10, decimal_places=2, default=0.00)
    status = models.TextField(db_column='status')

    class Meta:
        managed = False
        db_table = 'order_item'

    def __str__(self):
        return f"{self.order_id} {self.order_item_id}"


class Payment(models.Model):
    payment_id = models.AutoField(db_column='payment_id', primary_key=True)
    order_id = models.ForeignKey(Orders, db_column='order_id', on_delete=models.CASCADE)
    payment_date = models.DateTimeField(db_column='payment_date', auto_now_add=True)
    payment_method = models.CharField(max_length=100, db_column='payment_method')
    amount = models.DecimalField(db_column='amount',max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'payment'

    def __str__(self):
        return f"Payment {self.payment_id} for Order {self.order_id.order_id}"