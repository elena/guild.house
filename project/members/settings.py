# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.conf import settings


PAYMENT_METHODS = getattr(settings, 'MEMBERS_PAYMENT_METHODS',
                          (
                              ('paypal', 'paypal'),
                              ('in person', 'in person'),
                          ))