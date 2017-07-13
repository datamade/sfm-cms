from django.shortcuts import render
from django.views.generic.base import TemplateView


class About(TemplateView):
    template_name = 'pages/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class FAQ(TemplateView):
    template_name = 'pages/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class Help(TemplateView):
    template_name = 'pages/help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['help_tab'] = 'selected-tab'

        return context


class Countries(TemplateView):
    template_name = 'pages/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries_tab'] = 'selected-tab'

        return context
