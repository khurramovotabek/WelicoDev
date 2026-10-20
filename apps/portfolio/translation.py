from modeltranslation.translator import TranslationOptions, register

from .models import (
    Experience, Interest, JourneyStep, Milestone, Project, ProjectCategory, ProjectChallenge,
    ProjectFeature, ProjectImage, ProjectResult, Responsibility, Skill, SkillCategory,
)


@register(SkillCategory)
class SkillCategoryTR(TranslationOptions):
    fields = ("name",)


@register(Skill)
class SkillTR(TranslationOptions):
    fields = ("subtitle",)


@register(ProjectCategory)
class ProjectCategoryTR(TranslationOptions):
    fields = ("name",)


@register(Project)
class ProjectTR(TranslationOptions):
    fields = (
        "title", "subtitle", "short_description", "description", "project_type", "role",
        "duration", "team_size", "meta_title", "meta_description",
    )


@register(ProjectImage)
class ProjectImageTR(TranslationOptions):
    fields = ("caption",)


@register(ProjectFeature)
class ProjectFeatureTR(TranslationOptions):
    fields = ("title", "description")


@register(ProjectChallenge)
class ProjectChallengeTR(TranslationOptions):
    fields = ("text",)


@register(ProjectResult)
class ProjectResultTR(TranslationOptions):
    fields = ("label",)


@register(Experience)
class ExperienceTR(TranslationOptions):
    fields = ("role", "location", "summary", "description", "quote", "company_description", "company_industry",
              "degree", "field_of_study", "achievements")


@register(Responsibility)
class ResponsibilityTR(TranslationOptions):
    fields = ("text",)


@register(Milestone)
class MilestoneTR(TranslationOptions):
    fields = ("date_label", "title", "description")


@register(JourneyStep)
class JourneyStepTR(TranslationOptions):
    fields = ("title",)


@register(Interest)
class InterestTR(TranslationOptions):
    fields = ("title",)
