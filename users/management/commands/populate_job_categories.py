from django.core.management.base import BaseCommand
from django.utils.text import slugify
from users.models import JobCategory


class Command(BaseCommand):
    help = 'Populate job categories with default categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Plumbing',
                'description': 'Plumbing services including repairs, installations, and maintenance',
                'icon': 'wrench'
            },
            {
                'name': 'Electrical',
                'description': 'Electrical work including wiring, repairs, and installations',
                'icon': 'zap'
            },
            {
                'name': 'Cleaning',
                'description': 'House and commercial cleaning services',
                'icon': 'spray-can'
            },
            {
                'name': 'Carpentry',
                'description': 'Woodworking and carpentry services',
                'icon': 'hammer'
            },
            {
                'name': 'Painting',
                'description': 'Interior and exterior painting services',
                'icon': 'palette'
            },
            {
                'name': 'Landscaping',
                'description': 'Garden and landscaping services',
                'icon': 'tree-pine'
            },
            {
                'name': 'Moving',
                'description': 'Moving and relocation services',
                'icon': 'truck'
            },
            {
                'name': 'HVAC',
                'description': 'Heating, ventilation, and air conditioning services',
                'icon': 'air-vent'
            },
            {
                'name': 'Handyman',
                'description': 'General handyman and maintenance services',
                'icon': 'tools'
            },
            {
                'name': 'Other',
                'description': 'Other miscellaneous services',
                'icon': 'more-horizontal'
            },
        ]

        created_count = 0
        updated_count = 0

        for category_data in categories:
            slug = slugify(category_data['name'])
            
            category, created = JobCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': category_data['name'],
                    'description': category_data['description'],
                    'icon': category_data['icon'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                # Update existing category
                category.name = category_data['name']
                category.description = category_data['description']
                category.icon = category_data['icon']
                category.is_active = True
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated category: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} and updated {updated_count} job categories.'
            )
        ) 