from django.core.management.base import BaseCommand
from programs.models import ExerciseLibrary

EXERCISES = [
    # GLUTES
    {
        'name': 'Barbell Hip Thrust',
        'muscle_group': 'glutes',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-barbell-hip-thrust-front.mp4',
        'description': (
            'Sit with your upper back against a bench, barbell over your hips. '
            'Drive through your heels, squeeze your glutes at the top and lift your hips until your body is straight. '
            'Muscles worked: Gluteus Maximus (primary), Hamstrings, Core.'
        ),
    },
    {
        'name': 'Bulgarian Split Squat',
        'muscle_group': 'glutes',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-dumbbell-bulgarian-split-squat-front.mp4',
        'description': (
            'Place rear foot on a bench, front foot forward. Lower your back knee toward the floor, '
            'keeping chest tall. Push through the front heel to return. '
            'Muscles worked: Glutes, Quads, Hamstrings.'
        ),
    },
    {
        'name': 'Cable Kickback',
        'muscle_group': 'glutes',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/female-cable-kickback-side.mp4',
        'description': (
            'Attach ankle cuff to low cable. Lean slightly forward on the machine, '
            'kick one leg straight back squeezing the glute. Return slowly. '
            'Muscles worked: Gluteus Maximus.'
        ),
    },
    {
        'name': 'Sumo Deadlift',
        'muscle_group': 'glutes',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-barbell-sumo-deadlift-front.mp4',
        'description': (
            'Stand with feet wide, toes pointed out. Grip barbell inside your legs. '
            'Keep chest tall, drive hips forward to stand. '
            'Muscles worked: Glutes, Inner Thighs (Adductors), Hamstrings, Back.'
        ),
    },
    {
        'name': 'Glute Bridge',
        'muscle_group': 'glutes',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/female-bodyweight-glute-bridge-side.mp4',
        'description': (
            'Lie on your back, knees bent, feet flat. Drive hips up by squeezing glutes, '
            'hold 1 second at top. Lower slowly. '
            'Muscles worked: Gluteus Maximus, Hamstrings, Core.'
        ),
    },
    # LEGS
    {
        'name': 'Barbell Back Squat',
        'muscle_group': 'legs',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-barbell-squat-front.mp4',
        'description': (
            'Bar rests on upper traps. Feet shoulder-width apart. '
            'Sit back and down, keeping chest up and knees tracking over toes. '
            'Drive through heels to stand. '
            'Muscles worked: Quads, Glutes, Hamstrings, Core.'
        ),
    },
    {
        'name': 'Leg Press',
        'muscle_group': 'legs',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-machine-leg-press-side.mp4',
        'description': (
            'Sit in leg press machine, feet shoulder-width on platform. '
            'Lower platform until knees reach 90°, press back up without locking knees. '
            'Muscles worked: Quads, Glutes, Hamstrings.'
        ),
    },
    {
        'name': 'Romanian Deadlift',
        'muscle_group': 'legs',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-barbell-romanian-deadlift-side.mp4',
        'description': (
            'Hold barbell at hip level. Hinge at hips, pushing them back, '
            'lower bar along legs feeling hamstring stretch. Drive hips forward to return. '
            'Muscles worked: Hamstrings, Glutes, Lower Back.'
        ),
    },
    {
        'name': 'Leg Curl',
        'muscle_group': 'legs',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-machine-lying-leg-curl-side.mp4',
        'description': (
            'Lie face down on machine, pad behind ankles. Curl heels toward glutes, '
            'squeeze at top, lower slowly. '
            'Muscles worked: Hamstrings.'
        ),
    },
    {
        'name': 'Leg Extension',
        'muscle_group': 'legs',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-machine-leg-extension-side.mp4',
        'description': (
            'Sit in machine with pad across shins. Extend legs fully, squeeze quads at top, '
            'lower slowly. '
            'Muscles worked: Quadriceps.'
        ),
    },
    # BACK
    {
        'name': 'Lat Pulldown',
        'muscle_group': 'back',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-cable-lat-pulldown-front.mp4',
        'description': (
            'Grip bar wide, sit with thighs under pads. Pull bar to upper chest, '
            'leading with elbows. Return slowly. '
            'Muscles worked: Latissimus Dorsi, Biceps, Rear Deltoids.'
        ),
    },
    {
        'name': 'Seated Cable Row',
        'muscle_group': 'back',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-cable-seated-cable-row-side.mp4',
        'description': (
            'Sit on bench, feet on platform. Pull handle to lower abdomen, '
            'squeezing shoulder blades together. Return with control. '
            'Muscles worked: Middle Back (Rhomboids), Lats, Biceps.'
        ),
    },
    {
        'name': 'Barbell Bent-Over Row',
        'muscle_group': 'back',
        'difficulty': 'intermediate',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-barbell-bent-over-row-side.mp4',
        'description': (
            'Hinge forward ~45°, grip barbell. Row bar to lower chest, '
            'driving elbows back. Lower slowly. '
            'Muscles worked: Lats, Middle Back, Biceps, Rear Deltoids.'
        ),
    },
    # CHEST
    {
        'name': 'Dumbbell Chest Press',
        'muscle_group': 'chest',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-dumbbell-bench-press-side.mp4',
        'description': (
            'Lie on flat bench, dumbbells at chest level. Press up until arms nearly straight. '
            'Lower with control until elbows are at bench level. '
            'Muscles worked: Pectorals, Anterior Deltoids, Triceps.'
        ),
    },
    {
        'name': 'Cable Chest Fly',
        'muscle_group': 'chest',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-cable-cable-crossover-front.mp4',
        'description': (
            'Set cables at shoulder height. Step forward, arms slightly bent. '
            'Bring hands together in front of chest, squeezing pecs. '
            'Muscles worked: Pectorals (inner focus).'
        ),
    },
    # SHOULDERS
    {
        'name': 'Dumbbell Shoulder Press',
        'muscle_group': 'shoulders',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-dumbbell-shoulder-press-front.mp4',
        'description': (
            'Sit or stand, dumbbells at shoulder height, palms forward. '
            'Press overhead until arms are straight, lower slowly. '
            'Muscles worked: Deltoids (all heads), Triceps.'
        ),
    },
    {
        'name': 'Lateral Raise',
        'muscle_group': 'shoulders',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-dumbbell-lateral-raise-front.mp4',
        'description': (
            'Stand holding dumbbells at sides. Raise arms out to shoulder height '
            'with slight bend at elbow. Lower slowly. '
            'Muscles worked: Lateral (Middle) Deltoid.'
        ),
    },
    # ARMS
    {
        'name': 'Dumbbell Bicep Curl',
        'muscle_group': 'arms',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-dumbbell-bicep-curl-front.mp4',
        'description': (
            'Stand with dumbbells at sides, palms forward. Curl weights to shoulders, '
            'squeeze biceps at top. Lower slowly. '
            'Muscles worked: Biceps.'
        ),
    },
    {
        'name': 'Tricep Pushdown',
        'muscle_group': 'arms',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-cable-tricep-pushdown-front.mp4',
        'description': (
            'Stand at cable machine, grip bar at chest height. '
            'Push bar down until arms fully extended, squeeze triceps. Return slowly. '
            'Muscles worked: Triceps.'
        ),
    },
    # CORE
    {
        'name': 'Plank',
        'muscle_group': 'core',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/female-bodyweight-plank-side.mp4',
        'description': (
            'Forearms on floor, body straight from head to heels. '
            'Hold position, breathing steadily. Do not let hips sag or rise. '
            'Muscles worked: Core (Transverse Abdominis, Obliques), Glutes, Shoulders.'
        ),
    },
    {
        'name': 'Dead Bug',
        'muscle_group': 'core',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/female-bodyweight-dead-bug-side.mp4',
        'description': (
            'Lie on back, arms up, knees at 90°. Slowly lower opposite arm and leg toward floor '
            'keeping lower back pressed down. Return and switch sides. '
            'Muscles worked: Deep Core (Transverse Abdominis), Hip Flexors.'
        ),
    },
    {
        'name': 'Cable Crunch',
        'muscle_group': 'core',
        'difficulty': 'beginner',
        'photo_url': 'https://media.musclewiki.com/media/uploads/videos/branded/male-cable-cable-crunch-side.mp4',
        'description': (
            'Kneel at cable machine with rope at neck. Crunch torso down, '
            'rounding spine, bringing elbows toward knees. '
            'Muscles worked: Rectus Abdominis.'
        ),
    },
    # CARDIO
    {
        'name': 'Treadmill Walk (Incline)',
        'muscle_group': 'cardio',
        'difficulty': 'beginner',
        'photo_url': '',
        'description': (
            'Walk on treadmill at 10–15% incline, speed 5–6 km/h for 20–40 minutes. '
            'Low-impact cardio that targets glutes and hamstrings while burning fat. '
            'Excellent for clients with knee issues or who are new to exercise.'
        ),
    },
    {
        'name': 'Stationary Bike',
        'muscle_group': 'cardio',
        'difficulty': 'beginner',
        'photo_url': '',
        'description': (
            'Pedal at moderate resistance for 20–30 minutes. '
            'Adjust seat so knee is slightly bent at bottom of pedal stroke. '
            'Low-impact, joint-friendly cardio. Good for warm-up or fat burning.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed the exercise library with common exercises'

    def handle(self, *args, **options):
        created = 0
        for data in EXERCISES:
            obj, was_created = ExerciseLibrary.objects.get_or_create(
                name=data['name'],
                defaults={
                    'muscle_group': data['muscle_group'],
                    'difficulty': data['difficulty'],
                    'photo_url': data['photo_url'],
                    'description': data['description'],
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f'Done. {created} exercises created, {len(EXERCISES) - created} already existed.'
        ))
