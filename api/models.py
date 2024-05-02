from django.db import models
from django.utils.timezone import now
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.
class RawMaterials(models.Model):
    material_name = models.CharField(max_length=100, unique=True)
    material_min_stock = models.IntegerField(validators=[MinValueValidator(0)])
    material_unit = models.ForeignKey('Unit', on_delete=models.SET_NULL, null=True)
    material_note = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Raw Materials'
        ordering = ['material_name']

    def __str__(self):
        return str(self.material_name)

class Product(models.Model):
    PRODUCT_TYPE_CHOICES = (
        ("MANUFACTURED", "MANUFACTURED"), 
        ("IMPORTED", "IMPORTED"),
        ("LOCAL_PURCHASE", "LOCAL_PURCHASE")
        )
    product_name = models.CharField(max_length=100, unique=True)
    product_min_stock = models.IntegerField(validators=[MinValueValidator(0)])
    product_unit = models.ForeignKey('Unit', on_delete=models.SET_NULL, null=True)
    product_note = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now=True)
    product_type = models.CharField(choices=PRODUCT_TYPE_CHOICES, null=True, blank=True, default="", max_length=16)
    ingredients = models.ManyToManyField("RawMaterials", through='RawMaterials_Product')

    class Meta:
        ordering = ['product_name']

    def __str__(self):
        return str(self.product_name)

class RawMaterials_Product(models.Model):
    materials = models.ForeignKey("RawMaterials", on_delete=models.PROTECT, null=True)
    product = models.ForeignKey("Product", on_delete=models.PROTECT, null=True)
    quantity = models.DecimalField(decimal_places=4, max_digits=10)

    class Meta:
        verbose_name_plural = 'Raw Material to Product Formulation'

    def __str__(self):
        return str(self.product)

class RawMaterials_Inventory(models.Model):
    material_name = models.ForeignKey("RawMaterials", on_delete=models.PROTECT, null=True)
    supplier = models.ForeignKey("Supplier", on_delete=models.PROTECT, null=True)
    quantity = models.DecimalField(decimal_places=4, max_digits=10)
    material_stock_left = models.DecimalField(decimal_places=4, max_digits=10)
    material_cost = models.DecimalField(decimal_places=6, max_digits=15)
    material_total_cost = models.DecimalField(decimal_places=6, max_digits=18)
    ordered_date = models.DateField(default=now)
    created_at = models.DateTimeField(auto_now_add=True)
    order_update = models.DateTimeField(auto_now=True)
    inventory_note = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Raw Material Inventories'
        ordering = ['ordered_date', 'created_at', 'pk']

    def __str__(self):
        return str(f'{self.pk} -- {self.material_name}')
    
class RawMaterials_InventoryTransaction(models.Model):
    transaction_date = models.DateField(default=now)
    materials_inventory_pk = models.ForeignKey("RawMaterials_Inventory", on_delete=models.PROTECT, null=True, blank=True) # This is now like inventory
    m_quantity = models.DecimalField(decimal_places=4, max_digits=16, blank=True, null=True)
    product_inventory_pk = models.ForeignKey("Product_Inventory", on_delete=models.PROTECT, null=True, blank=True) # This is now like sales
    p_quantity = models.DecimalField(decimal_places=4, max_digits=16, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['transaction_date']

class Product_Inventory(models.Model):
    product_name = models.ForeignKey("Product", on_delete=models.PROTECT, null=True)
    supplier = models.ForeignKey("Supplier", on_delete=models.PROTECT, null=True)
    quantity = models.DecimalField(decimal_places=2, max_digits=10)
    product_stock_left = models.DecimalField(decimal_places=2, max_digits=10)
    product_cost = models.DecimalField(decimal_places=6, max_digits=15)
    product_total_cost = models.DecimalField(decimal_places=6, max_digits=18)
    ordered_date = models.DateField(default=now)
    order_update = models.DateTimeField(auto_now=True)
    inventory_note = models.TextField(null=True, blank=True)
    ingredients_transaction = models.ManyToManyField("RawMaterials_Inventory", through='RawMaterials_InventoryTransaction')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Product Inventories'
        ordering = ['ordered_date', "created_at", "pk"]

    def __str__(self):
        return str(f'{self.pk} -- {self.product_name}')
    
class InventoryTransaction(models.Model):
    transaction_date = models.DateField(default=now)
    sales_pk = models.ForeignKey("Sales", on_delete=models.PROTECT, null=True, blank=True)
    s_quantity = models.DecimalField(decimal_places=4, max_digits=16, blank=True, null=True)
    inventory_pk = models.ForeignKey("Product_Inventory", on_delete=models.PROTECT, null=True, blank=True)
    p_quantity = models.DecimalField(decimal_places=4, max_digits=16, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['transaction_date']
  
class Sales(models.Model):
    SALES_STATUS_CHOICES = (
        ("UNPAID", "UNPAID"), 
        ("PAID", "PAID"))
    sales_dr = models.CharField(max_length=10, default="", null=True, blank=True)
    sales_invoice = models.ForeignKey('SalesInvoice', on_delete=models.PROTECT, null=True, blank=True)
    sales_date = models.DateField(default=now)
    sales_updated = models.DateTimeField(auto_now=True)
    customer = models.ForeignKey('Customer', on_delete=models.PROTECT, null=True)
    product_name = models.ForeignKey("Product", on_delete=models.PROTECT, null=True)
    sales_quantity = models.DecimalField(decimal_places=2, max_digits=12)
    sales_unit_cost = models.DecimalField(decimal_places=2, max_digits=18)
    sales_total_cost = models.DecimalField(decimal_places=2, max_digits=24)

    sales_unit_price = models.DecimalField(decimal_places=6, max_digits=18)
    tax_percent = models.DecimalField(decimal_places=3, max_digits=6, null=True, blank=True, default=12)

    sales_note = models.TextField(null=True, blank=True, default="")

    # below computed
    sales_gross_price = models.DecimalField(decimal_places=6, max_digits=18, null=True, blank=True)
    sales_VAT = models.DecimalField(decimal_places=12, max_digits=24, null=True, blank=True)
    sales_total_price = models.DecimalField(decimal_places=6, max_digits=24)
    sales_margin = models.DecimalField(decimal_places=2, max_digits=15, null=True)
    sales_margin_percent = models.DecimalField(decimal_places=4, max_digits=15, null=True)

    sales_transaction = models.ManyToManyField("Product_Inventory", through='InventoryTransaction')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Sales'
        ordering = ['sales_date', 'created_at', 'pk']

    def __str__(self):
        return str(f'{self.pk} -- {self.product_name}')
    
    @property
    def sales_VAT(self):
        # return self.sales_gross_price * Decimal(0.12)
        if self.tax_percent is None:
            self.tax_percent = 12
        return round((self.sales_gross_price * Decimal(self.tax_percent / 100)), 2)
    @property
    def sales_gross_price(self):
        # return self.sales_total_price / Decimal(1.12)
        if self.tax_percent is None:
            self.tax_percent = 12
        return round((self.sales_unit_price * self.sales_quantity) / Decimal((self.tax_percent / 100) + 1), 2)
    @property
    def sales_total_price(self):
        return round((self.sales_gross_price + self.sales_VAT) , 2)
    @property
    def sales_margin(self):
        return round((self.sales_gross_price - self.sales_total_cost) , 2)
    @property
    def sales_margin_percent(self):
        if self.sales_total_cost == 0:
            return 0
        return round((self.sales_margin / self.sales_total_cost) * Decimal(100), 2)
    
class SalesInvoice(models.Model):
    STATUS_CHOICES = (
        ("UNPAID", "UNPAID"), 
        ("PAID", "PAID"))
    sales_invoice = models.CharField(max_length=150, unique=True)
    invoice_status = models.CharField(choices=STATUS_CHOICES, blank=True, default="UNPAID", max_length=6)
    invoice_date = models.DateTimeField(default=now)
    invoice_paid_date = models.DateTimeField(blank=True, null=True)
    invoice_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sales_invoice']

    def __str__(self):
        return str(self.sales_invoice)


class Customer(models.Model):
    company_name = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=50, default="", blank=True)
    contact_number = models.CharField(max_length=10, default="", blank=True)
    company_address = models.CharField(max_length=100, default="", blank=True)

    class Meta:
        ordering = ['company_name']

    def __str__(self):
        return str(self.company_name)
    
class Supplier(models.Model):
    company_name = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=50, default="", blank=True)
    contact_number = models.CharField(max_length=10, default="", blank=True)
    company_address = models.CharField(max_length=100, default="", blank=True)

    class Meta:
        ordering = ['company_name']

    def __str__(self):
        return str(self.company_name)
    
class Unit(models.Model):
    unit_name = models.CharField(max_length=50)
    unit_abbv = models.CharField(max_length=20)
    unit_category = models.ForeignKey('UnitCategory', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Product Units'

    def __str__(self):
        return str(self.unit_name)

class UnitCategory(models.Model):
    unit_category = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = 'Product Unit Category'

    def __str__(self):
        return str(self.unit_category)
    

