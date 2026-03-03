import re
import time
import urllib.request
from django.core.management.base import BaseCommand
from programs.models import ExerciseLibrary

GYMVISUAL_PAGES = {
    "Barbell Back Squat":      "https://gymvisual.com/animated-gifs/2909-barbell-high-bar-squat.html",
    "Barbell Bent-Over Row":   "https://gymvisual.com/animated-gifs/5930-dumbbell-bent-over-row-female.html",
    "Barbell Hip Thrust":      "https://gymvisual.com/animated-gifs/2520-barbell-hip-thrust.html",
    "Bulgarian Split Squat":   "https://gymvisual.com/animated-gifs/4904-dumbbell-bulgarian-split-squat-female.html",
    "Cable Chest Fly":         "https://gymvisual.com/animated-gifs/1648-cable-crossover-variation.html",
    "Cable Crunch":            "https://gymvisual.com/animated-gifs/4398-cable-kneeling-crunch-female.html",
    "Cable Kickback":          "https://gymvisual.com/animated-gifs/18257-cable-kneeling-glute-kickback-female.html",
    "Dead Bug":                "https://gymvisual.com/animated-gifs/1769-dead-bug.html",
    "Dumbbell Bicep Curl":     "https://gymvisual.com/animated-gifs/12016-dumbbell-curl-to-press-female.html",
    "Dumbbell Chest Press":    "https://gymvisual.com/animated-gifs/1782-dumbbell-bench-press.html",
    "Dumbbell Shoulder Press": "https://gymvisual.com/animated-gifs/4307-dumbbell-seated-shoulder-press-female.html",
    "Glute Bridge":            "https://gymvisual.com/animated-gifs/15304-bottle-weighted-glute-bridge-female.html",
    "Lat Pulldown":            "https://gymvisual.com/animated-gifs/4905-cable-wide-grip-lat-pulldown-female.html",
    "Lateral Raise":           "https://gymvisual.com/animated-gifs/4304-dumbbell-standing-lateral-raise-female.html",
    "Leg Curl":                "https://gymvisual.com/animated-gifs/2083-lever-lying-leg-curl.html",
    "Leg Extension":           "https://gymvisual.com/animated-gifs/4326-lever-leg-extension-female.html",
    "Leg Press":               "https://gymvisual.com/animated-gifs/4294-sled-45-degrees-leg-press-female.html",
    "Plank":                   "https://gymvisual.com/animated-gifs/4402-front-plank.html",
    "Romanian Deadlift":       "https://gymvisual.com/animated-gifs/4283-barbell-romanian-deadlift-female.html",
    "Seated Cable Row":        "https://gymvisual.com/animated-gifs/4315-cable-seated-row-female.html",
    "Stationary Bike":         "https://gymvisual.com/animated-gifs/4771-stationary-bike-run-version-3-female.html",
    "Sumo Deadlift":           "https://gymvisual.com/animated-gifs/5963-barbell-sumo-deadlift-female.html",
    "Treadmill Walk (Incline)": "https://gymvisual.com/animated-gifs/7984-walking-on-incline-treadmill.html",
    "Tricep Pushdown":         "https://gymvisual.com/animated-gifs/3735-cable-one-arm-tricep-pushdown.html",
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

GIF_RE = re.compile(r'https://gymvisual\.com/img/p/[\d/]+\.gif')


def fetch_gif_url(page_url):
    req = urllib.request.Request(page_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    match = GIF_RE.search(html)
    return match.group(0) if match else None


class Command(BaseCommand):
    help = 'Fetch animated GIF URLs from GymVisual and update ExerciseLibrary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be updated without saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        skipped = 0
        failed = 0

        for name, page_url in GYMVISUAL_PAGES.items():
            try:
                ex = ExerciseLibrary.objects.get(name=name)
            except ExerciseLibrary.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  [NOT FOUND] {name}'))
                skipped += 1
                continue

            self.stdout.write(f'Fetching {name}…', ending=' ')
            try:
                gif_url = fetch_gif_url(page_url)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR ({e})'))
                failed += 1
                time.sleep(1)
                continue

            if not gif_url:
                self.stdout.write(self.style.WARNING('no GIF found'))
                failed += 1
                time.sleep(1)
                continue

            self.stdout.write(self.style.SUCCESS(gif_url))

            if not dry_run:
                ex.photo_url = gif_url
                ex.save(update_fields=['photo_url'])
            updated += 1
            time.sleep(0.5)

        self.stdout.write('')
        self.stdout.write(f'Done: {updated} updated, {skipped} not found, {failed} failed.')
