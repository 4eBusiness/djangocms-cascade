# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import OrderedDict
try:
    from django.contrib.sites.shortcuts import get_current_site
except ImportError:
    from django.contrib.sites.models import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.forms import widgets
from django.utils import six
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from cms.utils.compat.dj import python_2_unicode_compatible
from cmsplugin_cascade.fields import PartialFormField
from cmsplugin_cascade.widgets import MultipleCascadingSizeWidget, ColorPickerWidget, SelectOverflowWidget


@python_2_unicode_compatible
class ExtraFieldsMixin(object):
    """
    This mixin class shall be added to plugins which shall offer extra fields for customizes
    CSS classes and styles.
    """
    EXTRA_INLINE_STYLES = OrderedDict((
        ('Margins', (('margin-top', 'margin-right', 'margin-bottom', 'margin-left',), MultipleCascadingSizeWidget)),
        ('Paddings', (('padding-top', 'padding-right', 'padding-bottom', 'padding-left',), MultipleCascadingSizeWidget)),
        ('Widths', (('min-width', 'width', 'max-width',), MultipleCascadingSizeWidget)),
        ('Heights', (('min-height', 'height', 'max-height',), MultipleCascadingSizeWidget)),
        ('Colors', (('color', 'background-color',), ColorPickerWidget)),
        ('Overflow', (('overflow', 'overflow-x', 'overflow-y',), SelectOverflowWidget)),
    ))

    def __str__(self):
        return self.plugin_class.get_identifier(self)

    def get_form(self, request, obj=None, **kwargs):
        from cmsplugin_cascade.models import PluginExtraFields

        glossary_fields = list(kwargs.pop('glossary_fields', self.glossary_fields))
        try:
            site = get_current_site(request)
            extra_fields = PluginExtraFields.objects.get(plugin_type=self.__class__.__name__, site=site)
        except ObjectDoesNotExist:
            pass
        else:
            # add a text input field to let the user name an ID tag for this HTML element
            if extra_fields.allow_id_tag:
                glossary_fields.append(PartialFormField('extra_element_id',
                    widgets.TextInput(),
                    label=_("Named Element ID"),
                ))

            # add a select box to let the user choose one or more CSS classes
            class_names = extra_fields.css_classes.get('class_names', '').replace(' ', '')
            if class_names:
                choices = [(clsname, clsname) for clsname in class_names.split(',')]
                if extra_fields.css_classes.get('multiple'):
                    widget = widgets.SelectMultiple(choices=choices)
                else:
                    widget = widgets.Select(choices=((None, _("Select CSS")),) + tuple(choices))
                glossary_fields.append(PartialFormField('extra_css_classes',
                    widget,
                    label=_("Customized CSS Classes"),
                    help_text=_("Customized CSS classes to be added to this element.")
                ))

            # add input fields to let the user enter styling information
            for style, choices_tuples in self.EXTRA_INLINE_STYLES.items():
                inline_styles = extra_fields.inline_styles.get('extra_fields:{0}'.format(style))
                if not inline_styles:
                    continue
                Widget = choices_tuples[1]
                if issubclass(Widget, MultipleCascadingSizeWidget):
                    key = 'extra_inline_styles:{0}'.format(style)
                    allowed_units = extra_fields.inline_styles.get('extra_units:{0}'.format(style)).split(',')
                    widget = Widget(inline_styles, allowed_units=allowed_units, required=False)
                    glossary_fields.append(PartialFormField(key, widget, label=style))
                else:
                    for inline_style in inline_styles:
                        key = 'extra_inline_styles:{0}'.format(inline_style)
                        label = '{0}: {1}'.format(style, inline_style)
                        glossary_fields.append(PartialFormField(key, Widget(), label=label))
        kwargs.update(glossary_fields=glossary_fields)
        return super(ExtraFieldsMixin, self).get_form(request, obj, **kwargs)

    @classmethod
    def get_css_classes(cls, obj):
        """Enrich list of CSS classes with customized ones"""
        css_classes = super(ExtraFieldsMixin, cls).get_css_classes(obj)
        extra_css_classes = obj.glossary.get('extra_css_classes')
        if isinstance(extra_css_classes, six.string_types):
            css_classes.append(extra_css_classes)
        elif isinstance(extra_css_classes, (list, tuple)):
            css_classes.extend(extra_css_classes)
        return css_classes

    @classmethod
    def get_inline_styles(cls, obj):
        """Enrich inline CSS styles with customized ones"""
        inline_styles = super(ExtraFieldsMixin, cls).get_inline_styles(obj)
        for key, eis in obj.glossary.items():
            if key.startswith('extra_inline_styles:'):
                if isinstance(eis, dict):
                    inline_styles.update(dict((k, v) for k, v in eis.items() if v))
                if isinstance(eis, (list, tuple)):
                    # the first entry of a sequence is used to disable an inline style
                    if eis[0] != 'on':
                        inline_styles.update({key.split(':')[1]: eis[1]})
                elif isinstance(eis, six.string_types):
                    inline_styles.update({key.split(':')[1]: eis})
        return inline_styles

    @classmethod
    def get_html_tag_attributes(cls, obj):
        attributes = super(ExtraFieldsMixin, cls).get_html_tag_attributes(obj)
        extra_element_id = obj.glossary.get('extra_element_id')
        if extra_element_id:
            attributes.update(id=extra_element_id)
        return attributes

    @classmethod
    def get_identifier(cls, obj):
        identifier = super(ExtraFieldsMixin, cls).get_identifier(obj)
        extra_element_id = obj.glossary and obj.glossary.get('extra_element_id')
        if extra_element_id:
            return format_html('{0}<em>{1}:</em> ', identifier, extra_element_id)
        return identifier
