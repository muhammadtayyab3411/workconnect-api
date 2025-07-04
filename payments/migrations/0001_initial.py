# Generated by Django 4.2.21 on 2025-05-27 18:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0009_alter_user_managers'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_event_id', models.CharField(max_length=100, unique=True)),
                ('event_type', models.CharField(max_length=100)),
                ('processed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('stripe_price_id_monthly', models.CharField(blank=True, max_length=100)),
                ('stripe_price_id_yearly', models.CharField(blank=True, max_length=100)),
                ('price_monthly', models.DecimalField(decimal_places=2, max_digits=10)),
                ('price_yearly', models.DecimalField(decimal_places=2, max_digits=10)),
                ('features', models.JSONField(default=list)),
                ('max_jobs_per_month', models.IntegerField(blank=True, null=True)),
                ('platform_fee_percentage', models.DecimalField(decimal_places=2, default=10.0, max_digits=5)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['price_monthly'],
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_customer_id', models.CharField(max_length=100)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('canceled', 'Canceled'), ('past_due', 'Past Due'), ('unpaid', 'Unpaid'), ('incomplete', 'Incomplete'), ('incomplete_expired', 'Incomplete Expired'), ('trialing', 'Trialing')], default='incomplete', max_length=50)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10)),
                ('current_period_start', models.DateTimeField()),
                ('current_period_end', models.DateTimeField()),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='payments.subscriptionplan')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='JobInvoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_invoice_id', models.CharField(blank=True, max_length=100, null=True)),
                ('stripe_payment_intent_id', models.CharField(blank=True, max_length=100, null=True)),
                ('job_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('platform_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stripe_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('worker_payout', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded'), ('canceled', 'Canceled')], default='pending', max_length=50)),
                ('due_date', models.DateTimeField()),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_invoices', to=settings.AUTH_USER_MODEL)),
                ('job', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='invoice', to='users.job')),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='worker_invoices', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_payment_method_id', models.CharField(max_length=100)),
                ('type', models.CharField(choices=[('card', 'Card'), ('bank_account', 'Bank Account')], max_length=50)),
                ('last_four', models.CharField(blank=True, max_length=4)),
                ('brand', models.CharField(blank=True, max_length=50)),
                ('exp_month', models.IntegerField(blank=True, null=True)),
                ('exp_year', models.IntegerField(blank=True, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=100)),
                ('account_holder_type', models.CharField(blank=True, max_length=50)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_methods', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'stripe_payment_method_id')},
            },
        ),
    ]
