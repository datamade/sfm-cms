from django.shortcuts import render
from django.views.generic.base import TemplateView

from pages.models import About, FAQ, Help, Countries, CountryOverview

default_text = """<p><i>No text yet...</i></p>"""


class AboutPage(TemplateView):
    template_name = 'pages/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['icon'] = 'fa-question-circle'

        try:
            about = About.objects.last()
            context['page'] = about
        except About.DoesNotExist:
            context['page'] = {'title': 'About',
                               'text': default_text}

        return context


class FAQPage(TemplateView):
    template_name = 'pages/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['icon'] = 'fa-question-circle'

        try:
            faq = FAQ.objects.last()
            context['page'] = faq
        except FAQ.DoesNotExist:
            context['page'] = {'title': 'Frequently Asked Questions',
                               'text': default_text}

        return context


class HelpPage(TemplateView):
    template_name = 'pages/help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['help_tab'] = 'selected-tab'
        context['icon'] = 'fa-question-circle'

        try:
            help_page = Help.objects.last()
            context['page'] = help_page
        except Help.DoesNotExist:
            context['page'] = {'title': 'Help',
                               'text': default_text}

        return context


class CountriesPage(TemplateView):
    template_name = 'pages/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            countries = CountryOverview.objects.all()
        except CountryOverview.DoesNotExist:
            countries = {}

        context['countries_tab'] = 'selected-tab'
        context['icon'] = 'fa-globe'
        context['countries'] = countries

        try:
            countries_page = Countries.objects.last()
            context['page'] = countries_page
        except Countries.DoesNotExist:
            context['page'] = {'title': 'Countries',
                               'text': default_text}

        return context

