
import re
import random
import string

from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from crowdfunding.models import Project, Pledge, Message, ProjectImage, ProjectUpdate
from datetime import date
from crowdfunding.constants import MAIL_NOT_SENT, CAMPAIGN_FULLY_BACKED_MAIL_SENT, \
        CAMPAIGN_EXPIRED_UNSUCCESSFULLY_MAIL_SENT, UPDATE_MAIL_NOT_SENT, UPDATE_MAIL_SENT
from lakshya.constants import CURRENCY_ISO_CODES


def generate_random_string(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def get_random_number(num_digits):
    """Generate and return a random number with the given number of digits"""
    range_start = 10 ** (num_digits - 1)
    range_end = (10 ** num_digits) - 1
    return random.randint(range_start, range_end)


# Removes all the non ASCII characters from the string
def removeNonAsciiChars(s):
    if not isinstance(s, str) and not isinstance(s, unicode):
        return str(s)
    if not s:
        return s
    return "".join(i for i in s if ord(i) < 128)


def format_and_split_name(name):
    """Given a name, do some basic formatting and return the first name and last name"""
    if not name:
        return ''
    name = removeNonAsciiChars(name).strip().title()
    words = name.split(' ', 1)
    if len(words) > 1:
        return words[0], words[1]
    else:
        return words[0], ''


def slugify(name):
    """Return slug for the given name"""
    if name is None:
        return None
    if not isinstance(name, str):
        name = unicode(name)

    name = name.strip().lower()
    # Any non word characters (letters, digits, and underscores) are replaced by '-'
    name = re.sub(r'\W+', '-', name)
    # Removing any trailing or leading dash
    name = re.sub(r'^-|-$', '', name)
    #Replace multiple continuous hipens with one
    name = re.sub('-+', '-', name)
    return name


def get_currency_iso_code(currency):
    return CURRENCY_ISO_CODES.get(currency, '')


def send_html_mail(subject, html_content, recipients, sender=None):
    """Send a HTML email from sender to one or many recipients"""
    if not isinstance(recipients, list):
        recipients = [recipients]
    if not sender:
        sender = settings.EMAIL_HOST_USER
    msg = EmailMultiAlternatives(subject, '', sender, recipients)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def send_email_from_template(template_name, context, subject, recipients):
    body = render_to_string(template_name, context)
    print "Subject: " + subject
    print "Recipients: " + recipients
    print "Body: " + body
    if recipients:
        send_html_mail(subject, body, recipients)
    else:
        print "******NO EMAIL ID FOR ABOVE******"



def send_cron_job_emails():
    projects = Project.objects.all()
    for count, project in enumerate(projects):
        if campaign_fully_backed(project):
            # This happens after campaign is fully backed AND is expired
            send_email_fully_funded_backers(project)
            send_email_fully_funded_author(project)
            update_project_sent_email_status(project, CAMPAIGN_FULLY_BACKED_MAIL_SENT)
        elif campaign_expired_unsuccessfully(project):
            send_email_campaign_unsuccessful_backers(project)
            send_email_campaign_unsuccessful_author(project)
            update_project_sent_email_status(project, CAMPAIGN_EXPIRED_UNSUCCESSFULLY_MAIL_SENT)
        elif campaign_within_three_days_expiry(project):
            send_email_campaign_close_to_expiry_author(project)
        if campaign_new_update(project):
            send_email_campaign_update_backers(project)
        if unfulfilled_pledges_exist(project):
            # If campaign eneded successfully and it has been over 10 days since it closed
            send_email_incomplete_pledges(project)



def campaign_fully_backed(project):
    # 'Project is successfully funded' mail is sent out after campaign period ends
    return (project.is_expired() and project.is_fully_pledged() and project.mail_status == MAIL_NOT_SENT)

def unfulfilled_pledges_exist(project):
    # Does this project have unfulfilled pldeges and has it been over 10 days since campaign ended
    unfulfilled_pledges = Pledge.objects.filter(project=project, pledge_fulfilled=False).all()
    days_since_campaign_ended = (date.today() - project.start_date).days - project.period
    return (project.is_expired() and project.is_fully_pledged() and unfulfilled_pledges and (days_since_campaign_ended in [5, 10, 12, 15, 20, 25]))

def campaign_expired_unsuccessfully(project):
    return (project.is_expired() and not project.is_fully_pledged() and \
                                        project.mail_status == MAIL_NOT_SENT)


def campaign_new_update(project):
    # Has there been an update in the last 24 hours?
    return (ProjectUpdate.objects.filter(project=project, mail_status=UPDATE_MAIL_NOT_SENT).exists())
    # return ((date.today() - project.updates.first().timestamp.date()).days <= 1)


def campaign_within_three_days_expiry(project):
    return project.get_days_remaining() in [3, 2, 1]


def update_project_sent_email_status(project, status):
    project.mail_status = status
    project.save()


def send_email_incomplete_pledges(project):
    days_since_campaign_ended = (date.today() - project.start_date).days - project.period
    subject = '[NITW Crowdfund] Fulfilling your pledge'
    template = 'emails/unfulfilled_pledge_backer.html'
    pledges = Pledge.objects.filter(project=project, pledge_fulfilled=False).all()
    # recipients = map(str,Pledge.objects.filter(project=project).values_list('user__email', flat=True))
    for pledge in pledges:
        context = {'pledge': pledge, 'days_since_campaign_ended': days_since_campaign_ended}
        recipient = pledge.user.email
        send_email_from_template(template, context, subject, recipient)

def send_email_fully_funded_backers(project):
    subject = '[NITW Crowdfund] Campaign you backed gets fully funded!'
    template = 'emails/campaign_closed_successfully_backer.html'
    pledges = Pledge.objects.filter(project=project).all()
    # recipients = map(str,Pledge.objects.filter(project=project).values_list('user__email', flat=True))
    for pledge in pledges:
        context = {'pledge': pledge}
        recipient = pledge.user.email
        send_email_from_template(template, context, subject, recipient)

def send_email_fully_funded_author(project):
    subject = '[NITW Crowdfund] Campaign Successfully Closed'
    context = {'project': project}
    template = 'emails/campaign_closed_successfully_author.html'
    recipient = project.author.email
    send_email_from_template(template, context, subject, recipient)

def send_email_campaign_unsuccessful_backers(project):
    subject = '[NITW Crowdfund] Campaign Ended'
    template = 'emails/campaign_unsuccessful_backer.html'
    pledges = Pledge.objects.filter(project=project).all()
    # recipients = map(str,Pledge.objects.filter(project=project).values_list('user__email', flat=True))
    for pledge in pledges:
        context = {'pledge': pledge}
        recipient = pledge.user.email
        send_email_from_template(template, context, subject, recipient)


def send_email_campaign_unsuccessful_author(project):
    subject = '[NITW Crowdfund] Campaign Ended'
    context = {'project': project}
    template = 'emails/campaign_unsuccessful_author.html'
    recipient = project.author.email
    send_email_from_template(template, context, subject, recipient)


def send_email_campaign_update_backers(project):
    subject = '[NITW Crowdfund] New Campaign Update'
    template = 'emails/project_updated_backer.html'
    pledges = Pledge.objects.filter(project=project).all()
    # recipients = map(str,Pledge.objects.filter(project=project).values_list('user__email', flat=True))
    for pledge in pledges:
        context = {'pledge': pledge, 'updates': ProjectUpdate.objects.filter(project=project, mail_status=UPDATE_MAIL_NOT_SENT)}
        recipient = pledge.user.email
        send_email_from_template(template, context, subject, recipient)
    ProjectUpdate.objects.filter(project=project, mail_status=UPDATE_MAIL_NOT_SENT).update(mail_status=UPDATE_MAIL_SENT)
        # ProjectUpdate.save()


def send_email_campaign_close_to_expiry_author(project):
    subject = '[NITW Crowdfund] Campaign closes in ' + str(project.get_days_remaining()) + ' days'
    context = {'project': project}
    template = 'emails/campaign_close_to_expiry_author.html'
    recipient = project.author.email
    send_email_from_template(template, context, subject, recipient)


    # collect list of projects, check for >=100% backing change, get list of emails for each project,
    # call send-email function with list of ids, html email template, record that email is sent for that project

