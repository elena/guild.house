from django.contrib import admin
from .models import GiftVoucher


class GiftVoucherAdmin(admin.ModelAdmin):

    list_display = [
        'number',
        'value',
        'issued_to',
        'issued_date',
        'expire_date',
        'added_by',
        'notes',
        'is_valid'
    ]

    list_filter = [
        'is_valid',
        'added_by'
    ]


admin.site.register(GiftVoucher, GiftVoucherAdmin)
