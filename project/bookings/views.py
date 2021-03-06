# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django.utils.timezone import localtime, now
from django.views import generic

from project.site.models import OpeningHours
from . import settings
from .forms import BookingForm, NewBookingForm, BlankForm
from .models import Booking
from .utils import import_revel_bookings


MSG_WARNING_BUSY = "Beware! HERE This booking made during a busy time. May conflict. Please check ASAP and contact to discuss options if necessary."  # noqa
MSG_WARNING_BUSY = MSG_WARNING_BUSY+"\n\r\n\r"
MSG_WARNING_BUSY = MSG_WARNING_BUSY+"The customer has been warned that this is the case and may be expecting confirmation."  # noqa
MSG_WARNING_BUSY_CUSTOMER = """Beware! As warned at time of booking: you have booked during a busy time it is possible that your booking may have conflicted with another.

We will contact you ASAP if this is the case. Alternatively you can contact us to double-check.
"""


class CalendarMixin(object):
    """ @TD: Fri Jun 24 11:46:48 AEST 2016: This is overkill, but was
    useful in a past time. Needs major clean up."""

    def get_calendar(self, context, yr=None, mth=None, day=None,
                     length=settings.DEFAULT_CALENDAR_LENGTH):
        if yr and mth:
            y = int(yr)
            m = int(mth)
        else:
            d = datetime.today()
            y = d.year
            m = d.month
            context['today'] = date(
                year=d.year, month=d.month, day=d.day)

        this_month = date(year=y, month=m, day=1)
        next_mth = this_month + relativedelta(months=+1)
        prev_mth = this_month + relativedelta(months=-1)
        context['cal_next_mth'] = '/%s/%02d/' % (next_mth.year, next_mth.month)
        context['cal_prev_mth'] = '/%s/%02d/' % (prev_mth.year, prev_mth.month)
        context['cal_next_yr'] = '/%s/%02d/' % (
            this_month.year + 1, this_month.month)
        context['cal_prev_yr'] = '/%s/%02d/' % (
            this_month.year - 1, this_month.month)
        context['month'] = this_month
        context['calendar'] = self.make_range(y, m, length)
        closed_dates = OpeningHours.objects.filter(
            date__gte=date.today(), is_closed=True)
        context['closed_dates'] = [x.date for x in closed_dates]
        return context

    def make_range(self, y, m, length):
        b = timedelta(days=length)

        # e = Booking.objects.filter(date__year=y, date__month=m)
        start = date.today() -\
            timedelta(date.today().weekday())
        end = start + b
        date_range = []
        while start < end:
            date_range.append({'day': start})
            # date_range.append({'day':start, 'events':e.filter(date=start)})
            start = start + timedelta(days=1)
        return date_range

    def get_context_data(self, *args, **kwargs):
        context = super(CalendarMixin, self).get_context_data(*args, **kwargs)
        context = self.get_calendar(context)
        context['tomorrow'] = date.today() + timedelta(days=1)
        return context


class TimeMixin(object):

    def get_booking_list(self, this_date):
        return Booking.objects.filter(reserved_date=this_date)

    def generate_time_dict(self, this_date):
        """requires `this_date` as :py:class:`datetime.date`

        This is used to fetch bookings and to `datetime.combine` with
        `datetime.time` to create the necessary range of times.
        """
        booking_list = self.get_booking_list(this_date)
        interval = settings.BOOKING_INTERVAL
        this_time = datetime.combine(this_date, settings.BOOKING_TIMES[0])
        end_time = datetime.combine(this_date, settings.BOOKING_TIMES[1])
        busy_night = False
        time_list, active_bookings, buffer_bookings, pax_dict = [], {}, {}, {}

        # create occupancy per time interval
        while this_time <= end_time:
            active_total, buffer_total = 0, 0
            bookings_at_this_time = booking_list.filter(
                reserved_time=this_time)
            pax_dict[this_time] = {}

            # Construct occupancy for this time
            if bookings_at_this_time:
                for booking in bookings_at_this_time:
                    active_bookings[booking.pk] = {
                        'pax': booking.party_size,
                        'dur': booking.booking_duration}
            for pk in active_bookings.keys():
                if active_bookings[pk]['dur']:
                    active_bookings[pk]['dur'] = active_bookings[pk]['dur'] - interval  # noqa
                    active_total = active_total + active_bookings[pk]['pax']
            pax_dict[this_time]['active'] = active_total

            # construct occupancy for the purpose of booking buffer
            # which has constant "duration"
            if bookings_at_this_time:
                for booking in bookings_at_this_time:
                    buffer_bookings[booking.pk] = {
                        'pax': booking.party_size,
                        'dur': settings.BUFFER_DURATION}
            for pk in buffer_bookings.keys():
                if buffer_bookings[pk]['dur']:
                    buffer_bookings[pk]['dur'] = buffer_bookings[pk]['dur'] - interval  # noqa
                    buffer_total = buffer_total + buffer_bookings[pk]['pax']
            pax_dict[this_time]['buffer'] = buffer_total
            this_time = this_time + interval

        this_time = datetime.combine(this_date, settings.BOOKING_TIMES[0])

        while this_time <= end_time:
            active = pax_dict[this_time]['active']

            if this_time+settings.BUFFER_DURATION > end_time:
                available = settings.CAPACITY - active
            else:
                available = settings.CAPACITY - \
                    (pax_dict[this_time]['active'] +
                     pax_dict[this_time+settings.BUFFER_DURATION]['buffer'])
            if available < 0:
                available = 0

            this_dict = {'pax': active,
                         'available': available,
                         'date': this_time,
                         'future': True,
                         'select_time': time(this_time.hour, this_time.minute),
                         'time': "{}:{:0>2}".format(this_time.hour,
                                                    this_time.minute)}

            for temp in settings.HEAT.keys():
                if this_dict['available'] > temp:
                    break
                else:
                    this_dict['heat'] = settings.HEAT[temp]

            if this_dict['pax'] > settings.CAPACITY:
                busy_night = True

            if this_date == now().date():
                # if this_time
                this_dict['future'] = False

            # Add `service` to dictionary
            for service_time, service in settings.SERVICE_TIMES:
                if time(this_time.hour, this_time.minute) == service_time:
                    this_dict['service'] = service

            time_list.append(this_dict)

            this_time = this_time + interval

        return time_list, busy_night

    def get_time_list(self, context, this_date):
        context['time_list'], context['busy_night'] = self.generate_time_dict(
            this_date)
        context['date'] = this_date
        context['booking_list'] = self.get_booking_list(this_date)

        # Sadly annotate too unreliable https://code.djangoproject.com/ticket/10060 # noqa E501
        total_pax = 0
        for booking in self.get_booking_list(this_date):
            total_pax = total_pax + booking.party_size
        context['pax_total'] = total_pax
        return context


class BookingFormMixin(object):

    def get_object(self):
        return get_object_or_404(Booking, code=self.kwargs.get('code'))

    def send_booking_notice_internal(self, obj, form, change="added"):
        warning = ""
        if "full" in form.cleaned_data.get('private_notes'):
            warning = MSG_WARNING_BUSY

        message = u"""Booking {change} in to system.

{warning}
Link to booking: http://guild.house/bookings/{code}/

Link to day: http://guild.house/bookings/{url_day}

        Add event to calendar (only if big event)
        What: {pax}pax {name}
        When: {time} {date} {day}
        """.format(change=change,
                   warning=warning,
                   code=obj.code,
                   url=obj.get_absolute_url(),
                   method=form.cleaned_data.get('booking_method'),
                   day=form.cleaned_data.get('reserved_date').strftime('%a'),
                   time=str(form.cleaned_data.get('reserved_time')),
                   date=form.cleaned_data.get(
                       'reserved_date').strftime('%d-%b-%Y'),
                   url_day=form.cleaned_data.get(
                       'reserved_date').strftime('%Y/%m/%d/'),
                   pax=form.cleaned_data.get('party_size'),
                   name=form.cleaned_data.get('name'),
                   )
        subject = "[{method}] {name} {pax}pax {date} ".format(
            method=form.cleaned_data.get('booking_method'),
            date=form.cleaned_data.get('reserved_date').strftime('%a %d-%b'),
            pax=form.cleaned_data.get('party_size'),
            name=form.cleaned_data.get('name')
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.FROM_EMAIL,
            recipient_list=settings.TO_EMAILS,
        )
        return True

    def send_booking_notice_customer(self, obj, form):
        warning = ""
        if "full" in form.cleaned_data.get('private_notes'):
            warning = MSG_WARNING_BUSY_CUSTOMER

        message = u"""Thank you for making a reservation at Guild!

Name: {name}
Number of people: {pax}pax
When: {time}, {day} {date}
{warning}
Link to booking details: http://guild.house/bookings/{code}/success/

If you would like to contact us for any reason:
Call us on: 02 6257 2727
Email: hello@guild.house
Web: http://guild.house

--
Regards,
Automated Bookings Robot-Machine
-Guild Team

facebook.com/guildhouse.canberra
(02) 6257 2727
Open 7 days, 12pm til late
        """.format(code=obj.code,
                   warning=warning,
                   url=obj.get_absolute_url(),
                   method=form.cleaned_data.get('booking_method'),
                   day=form.cleaned_data.get('reserved_date').strftime('%a'),
                   time=str(form.cleaned_data.get('reserved_time')),
                   date=form.cleaned_data.get(
                       'reserved_date').strftime('%d-%b-%Y'),
                   pax=form.cleaned_data.get('party_size'),
                   name=form.cleaned_data.get('name'),
                   )
        subject = "[{method}] {name} {pax}pax {date} ".format(
            method=form.cleaned_data.get('booking_method'),
            date=form.cleaned_data.get('reserved_date').strftime('%a %d-%b'),
            pax=form.cleaned_data.get('party_size'),
            name=form.cleaned_data.get('name')
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.FROM_EMAIL,
            recipient_list=[form.cleaned_data.get('email')],
        )
        return True


class BookingQueryset(object):

    model = Booking
    allow_future = True
    date_field = 'reserved_date'
    month_format = '%m'
    week_format = "%W"
    paginate_by = settings.BOOKINGS_PAGINATE_BY

    def get_context_data(self, *args, **kwargs):
        context = super(BookingQueryset, self).get_context_data(
            *args, **kwargs)
        context['future_list'] = self.get_queryset().future()
        context['summary_list'] = self.get_queryset().today()\
                                      .values('reserved_date')\
                                      .annotate(count=Count('id'),
                                                pax=Sum('party_size'))\
                                      .order_by('reserved_date')
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super(BookingQueryset, self).get_queryset(*args, **kwargs)
        return queryset.active().order_by('reserved_date', 'reserved_time')

    def get_heat(self, qty):
        if not qty:
            return ''
        if qty < 0:
            qty = 0
        tmp = ''
        for temp in settings.HEAT.keys():
            if settings.CAPACITY-qty > temp:
                return tmp
            else:
                tmp = settings.HEAT[temp]
        return tmp

    def get_service_totals(self, obj_list):
        services = []

        early_pax = obj_list.filter(
            service='early').aggregate(Sum('party_size'))['party_size__sum']
        if early_pax:
            services.append({'service': 'early',
                             'pax': early_pax,
                             'heat': self.get_heat(early_pax)})
        for serv in settings.SERVICE_CHOICE:
            pax = obj_list.filter(service=serv[0]).aggregate(
                Sum('party_size'))['party_size__sum']
            services.append({'service': serv[0],
                             'pax': pax,
                             'heat': self.get_heat(pax)})
        return services

    def get_queryset_by_day(self, *args, **kwargs):
        queryset = super(BookingQueryset, self).get_queryset(*args, **kwargs)
        return queryset.active().order_by('reserved_date', 'reserved_time')


class BookingTimeView(BookingQueryset, TimeMixin, generic.ListView):

    template_name = 'bookings/_time.html'

    def get_context_data(self, *args, **kwargs):
        context = super(BookingTimeView, self).get_context_data(
            *args, **kwargs)
        context = self.get_time_list(context,
                                     this_date=date(int(self.kwargs['year']),
                                                    int(self.kwargs['month']),
                                                    int(self.kwargs['day']))
                                     )
        return context


class BookingSuccessView(BookingQueryset, generic.DetailView):

    template_name = 'bookings/booking_success.html'

    def get_object(self):
        return get_object_or_404(Booking, code=self.kwargs.get('code'))

    def get_context_data(self, *args, **kwargs):
        context = super(BookingSuccessView, self).get_context_data(
            *args, **kwargs)
        context['big_booking'] = settings.BIG_BOOKING
        return context


class BookingRunView(LoginRequiredMixin, BookingQueryset, generic.DetailView):

    template_name = 'bookings/run_sheet.html'

    def get_object(self):
        return get_object_or_404(Booking, code=self.kwargs.get('code'))

    def get_context_data(self, *args, **kwargs):
        context = super(BookingRunView, self).get_context_data(
            *args, **kwargs)
        context['other_bookings'] = Booking.objects.filter(
            reserved_date=self.get_object().reserved_date)
        return context


class BookingCreateView(BookingFormMixin, CalendarMixin, BookingQueryset,
                        TimeMixin, generic.edit.CreateView):

    form_class = NewBookingForm

    def form_valid(self, form):
        obj = form.instance
        obj.save()
        self.send_booking_notice_internal(obj=obj, form=form, change="added")
        self.send_booking_notice_customer(obj=obj, form=form)
        return redirect('bookings:booking_success', code=form.instance.code)

    def get_context_data(self, *args, **kwargs):
        context = super(BookingCreateView, self).get_context_data(
            *args, **kwargs)
        context = self.get_calendar(context)
        context['today'] = date.today()
        context['now'] = now
        context = self.get_time_list(context, this_date=date.today())
        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(BookingCreateView, self).get_form_kwargs(
            *args, **kwargs)
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_initial(self):
        initial = super(BookingCreateView, self).get_initial()
        initial = initial.copy()

        if self.request.user.is_authenticated():
            initial['user'] = self.request.user
            initial['email'] = 'foh.managers@guild.house'

        # Set as tomorrow if booking made later than 6pm.
        if localtime(now()).hour > 18:
            initial['reserved_date'] = date.today() + timedelta(days=1)
        else:
            initial['reserved_date'] = date.today()
        initial['reserved_time'] = settings.DEFAULT_BOOKING_TIME
        initial['booking_duration'] = settings.DEFAULT_BOOKING_DURATION
        initial['booking_method'] = settings.DEFAULT_BOOKING_METHOD

        return initial


class BookingUpdateView(LoginRequiredMixin, BookingFormMixin, CalendarMixin,
                        BookingQueryset, generic.edit.UpdateView):

    slug_field = 'code'
    form_class = BookingForm

    def form_valid(self, form):
        obj = form.instance
        obj.updated_by = self.request.user
        obj.save()
        self.send_booking_notice_internal(obj=obj, form=form, change="updated")
        self.send_booking_notice_customer(obj=obj, form=form)
        return redirect('bookings:booking_update', code=form.instance.code)

    def get_object(self):
        if not self.request.user.is_authenticated():
            raise Http404()
        else:
            return get_object_or_404(Booking, code=self.kwargs.get('code'))

    def get_context_data(self, *args, **kwargs):
        context_data = super(
            BookingUpdateView, self).get_context_data(*args, **kwargs)

        context_data['update_view'] = True
        return context_data


class BookingListView(BookingQueryset, CalendarMixin, generic.ListView):

    def get(self, *args, **kwargs):
        page = self.kwargs.get('page', None)
        if page is not None and int(page) < 2:
            return redirect('bookings:booking_list', permanent=True)
        return super(BookingListView, self).get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context_data = super(BookingListView, self).get_context_data(*args,
                                                                     **kwargs)

        context_data = self.get_calendar(context_data)

        qs = self.get_queryset().future()
        calendar = context_data['calendar']
        for x in calendar:
            x['services'] = self.get_service_totals(
                qs.filter(reserved_date=x['day']))

        context_data['show_all'] = True
        return context_data


class BookingListNumView(LoginRequiredMixin, BookingListView):

    template_name = 'bookings/bookings_nums.html'


class BookingFutureView(LoginRequiredMixin, generic.ListView):

    model = Booking
    template_name = 'bookings/bookings_table.html'

    def get_queryset(self, *args, **kwargs):
        queryset = super(BookingFutureView, self).get_queryset(*args, **kwargs)
        return queryset.future()

    def get_context_data(self, *args, **kwargs):
        get_future_services_set()
        context_data = super(
            BookingFutureView, self).get_context_data(*args, **kwargs)
        context_data['future_days_list'] = context_data['object_list']
        return context_data


class BookingCancelledView(BookingQueryset, generic.ListView):

    template_name = 'bookings/booking_list_cancelled.html'

    def get_queryset(self, *args, **kwargs):
        # queryset = super(BookingCancelledView, self).get_queryset(*args, **kwargs)
        return Booking.objects.filter(status__in=['cancelled', 'no_show']).order_by('-updated_at')


class BookingYearArchiveView(BookingQueryset, generic.YearArchiveView):

    make_object_list = True


class BookingMonthArchiveView(BookingQueryset, generic.MonthArchiveView):

    pass


class BookingDayArchiveView(BookingQueryset, generic.DayArchiveView):

    def get_context_data(self, *args, **kwargs):
        context_data = super(BookingDayArchiveView,
                             self).get_context_data(*args, **kwargs)

        obj_list = kwargs.get('object_list')
        context_data['total'] = obj_list.aggregate(Sum('party_size'))
        context_data['services'] = self.get_service_totals(obj_list)
        context_data['cancelled_list'] = self.get_dated_queryset() \
            .filter(status='Cancelled') \
            .order_by('name')
        return context_data


class BookingTodayArchiveView(generic.RedirectView):

    def get_redirect_url(self):
        return reverse('bookings:booking_day', kwargs={
            'year': date.today().year,
            'month': "{:0>2}".format(date.today().month),
            'day': "{:0>2}".format(date.today().day)
        })


class BookingWeekArchiveView(BookingQueryset, generic.WeekArchiveView):

    pass


class BookingDetailView(BookingQueryset, generic.DetailView):

    pass


class FormView(generic.FormView):

    template_name = 'bookings/default_form.html'
    form_class = BlankForm
    success_url = "/bookings/post/"


def post_view(request):

    template_name = 'bookings/default_form.html'
    context_data = {}

    if request.method == 'POST':
        form = BlankForm(request.POST)
        if form.is_valid():
            context_data['success_obj'] = import_revel_bookings(
                request.POST['input_data'])

    else:
        form = BlankForm()

    context_data['form'] = form
    return render(request, template_name, context_data)
