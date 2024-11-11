from django.db import models


class Customers(models.Model):
    customernumber = models.IntegerField(db_column='customerNumber', primary_key=True)  # Field name made lowercase.
    customername = models.CharField(db_column='customerName', max_length=50)  # Field name made lowercase.
    contactlastname = models.CharField(db_column='contactLastName', max_length=50)  # Field name made lowercase.
    contactfirstname = models.CharField(db_column='contactFirstName', max_length=50)  # Field name made lowercase.
    phone = models.CharField(max_length=50)
    addressline1 = models.CharField(db_column='addressLine1', max_length=50)  # Field name made lowercase.
    addressline2 = models.CharField(db_column='addressLine2', max_length=50, blank=True, null=True)  # Field name made lowercase.
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50, blank=True, null=True)
    postalcode = models.CharField(db_column='postalCode', max_length=15, blank=True, null=True)  # Field name made lowercase.
    country = models.CharField(max_length=50)
    salesrepemployeenumber = models.ForeignKey('Employees', models.DO_NOTHING, db_column='salesRepEmployeeNumber', blank=True, null=True)  # Field name made lowercase.
    creditlimit = models.DecimalField(db_column='creditLimit', max_digits=10, decimal_places=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'customers'


class Employees(models.Model):
    employeenumber = models.IntegerField(db_column='employeeNumber', primary_key=True)  # Field name made lowercase.
    lastname = models.CharField(db_column='lastName', max_length=50)  # Field name made lowercase.
    firstname = models.CharField(db_column='firstName', max_length=50)  # Field name made lowercase.
    extension = models.CharField(max_length=10)
    email = models.CharField(max_length=100)
    officecode = models.ForeignKey('Offices', models.DO_NOTHING, db_column='officeCode')  # Field name made lowercase.
    reportsto = models.ForeignKey('self', models.DO_NOTHING, db_column='reportsTo', blank=True, null=True)  # Field name made lowercase.
    jobtitle = models.CharField(db_column='jobTitle', max_length=50)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'employees'


class Offices(models.Model):
    officecode = models.CharField(db_column='officeCode', primary_key=True, max_length=10)  # Field name made lowercase.
    city = models.CharField(max_length=50)
    phone = models.CharField(max_length=50)
    addressline1 = models.CharField(db_column='addressLine1', max_length=50)  # Field name made lowercase.
    addressline2 = models.CharField(db_column='addressLine2', max_length=50, blank=True, null=True)  # Field name made lowercase.
    state = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50)
    postalcode = models.CharField(db_column='postalCode', max_length=15)  # Field name made lowercase.
    territory = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'offices'


class Orderdetails(models.Model):
    ordernumber = models.OneToOneField('Orders', models.DO_NOTHING, db_column='orderNumber', primary_key=True)  # Field name made lowercase. The composite primary key (orderNumber, productCode) found, that is not supported. The first column is selected.
    productcode = models.ForeignKey('Products', models.DO_NOTHING, db_column='productCode')  # Field name made lowercase.
    quantityordered = models.IntegerField(db_column='quantityOrdered')  # Field name made lowercase.
    priceeach = models.DecimalField(db_column='priceEach', max_digits=10, decimal_places=2)  # Field name made lowercase.
    orderlinenumber = models.SmallIntegerField(db_column='orderLineNumber')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'orderdetails'
        unique_together = (('ordernumber', 'productcode'),)


class Orders(models.Model):
    ordernumber = models.IntegerField(db_column='orderNumber', primary_key=True)  # Field name made lowercase.
    orderdate = models.DateField(db_column='orderDate')  # Field name made lowercase.
    requireddate = models.DateField(db_column='requiredDate')  # Field name made lowercase.
    shippeddate = models.DateField(db_column='shippedDate', blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(max_length=15)
    comments = models.TextField(blank=True, null=True)
    customernumber = models.ForeignKey(Customers, models.DO_NOTHING, db_column='customerNumber')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'orders'


class Payments(models.Model):
    customernumber = models.OneToOneField(Customers, models.DO_NOTHING, db_column='customerNumber', primary_key=True)  # Field name made lowercase. The composite primary key (customerNumber, checkNumber) found, that is not supported. The first column is selected.
    checknumber = models.CharField(db_column='checkNumber', max_length=50)  # Field name made lowercase.
    paymentdate = models.DateField(db_column='paymentDate')  # Field name made lowercase.
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'payments'
        unique_together = (('customernumber', 'checknumber'),)


class Productlines(models.Model):
    productline = models.CharField(db_column='productLine', primary_key=True, max_length=50)  # Field name made lowercase.
    textdescription = models.CharField(db_column='textDescription', max_length=4000, blank=True, null=True)  # Field name made lowercase.
    htmldescription = models.TextField(db_column='htmlDescription', blank=True, null=True)  # Field name made lowercase.
    image = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'productlines'


class Products(models.Model):
    productcode = models.CharField(db_column='productCode', primary_key=True, max_length=15)  # Field name made lowercase.
    productname = models.CharField(db_column='productName', max_length=70)  # Field name made lowercase.
    productline = models.ForeignKey(Productlines, models.DO_NOTHING, db_column='productLine')  # Field name made lowercase.
    productscale = models.CharField(db_column='productScale', max_length=10)  # Field name made lowercase.
    productvendor = models.CharField(db_column='productVendor', max_length=50)  # Field name made lowercase.
    productdescription = models.TextField(db_column='productDescription')  # Field name made lowercase.
    quantityinstock = models.SmallIntegerField(db_column='quantityInStock')  # Field name made lowercase.
    buyprice = models.DecimalField(db_column='buyPrice', max_digits=10, decimal_places=2)  # Field name made lowercase.
    msrp = models.DecimalField(db_column='MSRP', max_digits=10, decimal_places=2)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'products'

