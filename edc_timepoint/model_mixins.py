from django.apps import apps as django_apps
from django.db import models

from .choices import TIMEPOINT_STATUS
from .constants import OPEN_TIMEPOINT, CLOSED_TIMEPOINT, FEEDBACK
from django.utils import timezone


class TimepointError(Exception):
    pass


class TimepointStatusMixin(models.Model):

    timepoint_status = models.CharField(
        max_length=15,
        choices=TIMEPOINT_STATUS,
        default=OPEN_TIMEPOINT)

    # this is the original calculated appointment datetime
    # updated in the signal
    timepoint_opened_datetime = models.DateTimeField(
        null=True,
        editable=False)

    timepoint_closed_datetime = models.DateTimeField(
        null=True,
        editable=False)

    def save(self, *args, **kwargs):
        if (kwargs.get('update_fields') != ['timepoint_status'] and
                kwargs.get('update_fields') != ['timepoint_opened_datetime', 'timepoint_status'] and
                kwargs.get('update_fields') != ['timepoint_closed_datetime', 'timepoint_status']):
            app_config = django_apps.get_app_config('edc_timepoint')
            try:
                timepoint = app_config.timepoints[self._meta.label_lower]
            except KeyError:
                raise TimepointError(
                    'Model \'{}\' is not configured as a timepoint. '
                    'See AppConfig for \'edc_timepoint\'.'.format(self._meta.label_lower))
            if getattr(self, timepoint.status_field) != timepoint.closed_status:
                self.timepoint_status = OPEN_TIMEPOINT
                self.timepoint_closed_datetime = None
            elif self.timepoint_status == CLOSED_TIMEPOINT:
                raise TimepointError(
                    'This \'{}\' instance is closed for data entry. See Timpoint.'.format(self._meta.verbose_name))
        super(TimepointStatusMixin, self).save(*args, **kwargs)

    def timepoint_close_timepoint(self):
        """Closes a timepoint."""
        app_config = django_apps.get_app_config('edc_timepoint')
        timepoint = app_config.timepoints[self._meta.label_lower]
        if getattr(self, timepoint.status_field) == timepoint.closed_status:
            self.timepoint_status = CLOSED_TIMEPOINT
            self.timepoint_closed_datetime = timezone.now()
            self.save(update_fields=['timepoint_status'])

    def timepoint_open_timepoint(self):
        """Re-opens a timepoint."""
        if self.timepoint_status == CLOSED_TIMEPOINT:
            self.timepoint_status = OPEN_TIMEPOINT
            self.timepoint_closed_datetime = None
            self.save(update_fields=['timepoint_closed_datetime', 'timepoint_status'])

    def timepoint(self):
        """Formats and returns the status for the change_list."""
        if self.timepoint_status == OPEN_TIMEPOINT:
            return '<span style="color:green;">Open</span>'
        elif self.timepoint_status == CLOSED_TIMEPOINT:
            return '<span style="color:red;">Closed</span>'
        elif self.timepoint_status == FEEDBACK:
            return '<span style="color:orange;">Feedback</span>'
    timepoint.allow_tags = True

    class Meta:
        abstract = True
