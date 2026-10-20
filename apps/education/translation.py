from modeltranslation.translator import TranslationOptions, register

from .models import Course, Lesson, LessonResource, Module


@register(Course)
class CourseTR(TranslationOptions):
    fields = ("title", "subtitle", "description", "what_you_learn", "requirements", "for_whom", "meta_title", "meta_description")


@register(Module)
class ModuleTR(TranslationOptions):
    fields = ("title",)


@register(Lesson)
class LessonTR(TranslationOptions):
    fields = ("title", "summary", "content", "homework")


@register(LessonResource)
class LessonResourceTR(TranslationOptions):
    fields = ("title",)
