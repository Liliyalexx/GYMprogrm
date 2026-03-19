import httpx
import os
from datetime import date
from django.core.management.base import BaseCommand
from django.conf import settings
from students.models import Student


def _send_email(to_email, subject, body):
    api_key = getattr(settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        print(f'[payment reminder] no RESEND_API_KEY — skipping email to {to_email}')
        return False
    try:
        resp = httpx.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'from': 'GYMprogrm <noreply@gymprogrm.org>',
                'to': [to_email],
                'subject': subject,
                'text': body,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        print(f'[payment reminder] FAILED for {to_email}: {exc}')
        return False


class Command(BaseCommand):
    help = 'Send payment reminder emails to students whose payment is due soon or overdue.'

    def handle(self, *args, **options):
        today = date.today()
        students = Student.objects.filter(
            is_active=True,
            intake_status='active',
            payment_start_date__isnull=False,
            email__gt='',
        ).exclude(payment_status='paid')

        sent = 0
        for student in students:
            days_until = student.payment_days_until()
            if days_until is None:
                continue

            # Decide if we should send a reminder today
            if days_until == 3:
                kind = 'due_soon'
                subject = 'Your GYMprogrm payment is due in 3 days'
                body = (
                    f'Hi {student.name},\n\n'
                    f'This is a reminder that your training subscription ({student.get_payment_plan_display()}) '
                    f'payment is due in 3 days.\n\n'
                    f'Please send your payment to your trainer via {student.get_payment_method_display() if student.payment_method else "your agreed method"}.\n\n'
                    f'View your billing details at: https://gymprogrm.org/portal/billing/\n\n'
                    f'— GYMprogrm'
                )
            elif days_until == 0:
                kind = 'due_today'
                subject = 'Your GYMprogrm payment is due today'
                body = (
                    f'Hi {student.name},\n\n'
                    f'Your training subscription ({student.get_payment_plan_display()}) payment is due today.\n\n'
                    f'Please send your payment to your trainer via {student.get_payment_method_display() if student.payment_method else "your agreed method"}.\n\n'
                    f'View your billing details at: https://gymprogrm.org/portal/billing/\n\n'
                    f'— GYMprogrm'
                )
            elif days_until == -1:
                kind = 'overdue'
                subject = 'Your GYMprogrm payment is overdue'
                body = (
                    f'Hi {student.name},\n\n'
                    f'Your training subscription ({student.get_payment_plan_display()}) payment was due yesterday and is now overdue.\n\n'
                    f'Please send your payment to your trainer as soon as possible.\n\n'
                    f'View your billing details at: https://gymprogrm.org/portal/billing/\n\n'
                    f'— GYMprogrm'
                )
            else:
                continue

            # Skip if already sent a reminder today
            if student.payment_reminder_sent_date == today:
                self.stdout.write(f'  skip {student.name} — already sent today')
                continue

            ok = _send_email(student.email, subject, body)
            if ok:
                student.payment_reminder_sent_date = today
                student.save(update_fields=['payment_reminder_sent_date'])
                sent += 1
                self.stdout.write(f'  ✓ sent {kind} reminder to {student.name} <{student.email}>')

        self.stdout.write(self.style.SUCCESS(f'Done — {sent} reminder(s) sent.'))
