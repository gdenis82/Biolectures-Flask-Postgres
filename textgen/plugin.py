import os
from openai import OpenAI
import datetime
from flask import Blueprint, current_app, request, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app import db
from auth.views import admin_required

load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

textgen_bp = Blueprint('textgen', __name__, url_prefix='/api/textgen')

# Dictionary of prompt templates for different tasks
PROMPT_TEMPLATES = {
    'friendly': "Перепиши этот текст более дружелюбно, сохрани смысл:\n\n{text}",
    'seo': """Перепиши описание лекции для SEO-оптимизации, сделай его уникальным, сохраняя ключевые слова и основной смысл. 
    Добавь релевантные ключевые слова и улучши читаемость. Удали спецсимволы, оставь только знаки препинания. 
    Не добавляй никаких заголовков, не пиши Название лекции, Описание, Ключевые слова и т. д. Верни только сам улучшенный текст, без абзацев и переноса строк.
    Текст не больше 350 символов. :\n\n{text}"""
}

def generate_text(text, task_type='friendly', model="gpt-4o-mini", temperature=0.7, max_tokens=300):
    """
    Universal function to generate text using OpenAI API

    Args:
        text (str): The base text to process
        task_type (str): Type of task ('friendly', 'seo', etc.)
        model (str): OpenAI model to use
        temperature (float): Creativity parameter (0.0-1.0)
        max_tokens (int): Maximum tokens in the response

    Returns:
        str: Generated text or None if error
    """
    if not text:
        return None

    # Get the appropriate prompt template or use friendly as default
    prompt_template = PROMPT_TEMPLATES.get(task_type, PROMPT_TEMPLATES['friendly'])
    prompt = prompt_template.format(text=text)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt},
                      {"role": "system", "content": "Ты опытный редактор, оптимизирующий тексты под SEO. Пиши кратко, понятно и без структурных заголовков."}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        current_app.logger.error(f"OpenAI error: {e}")
        return None

def _update_lecture_descriptions_impl():
    """
    Implementation of the update logic - should be called within an app context
    """
    from models.models import Lecture

    # Get current time
    now = datetime.datetime.utcnow()

    # Find lectures that need description update (updated more than 7 days ago)
    seven_days_ago = now - datetime.timedelta(days=15)
    lectures_to_update = Lecture.query.filter(
        Lecture.updated_at <= seven_days_ago,
        Lecture.description.isnot(None),
        Lecture.is_active == True
    ).all()

    current_app.logger.info(f"Found {len(lectures_to_update)} lectures to update descriptions")

    # Update each lecture description
    for lecture in lectures_to_update:
        if not lecture.content:
            continue

        # Generate new SEO-optimized description
        new_description = generate_text(f"{lecture.title}. {lecture.content}", task_type='seo')

        if new_description:
            lecture.description = new_description
            lecture.updated_at = now

            try:
                db.session.commit()
                current_app.logger.info(f"Updated description for lecture ID: {lecture.id}")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating lecture ID {lecture.id}: {e}")

def update_lecture_descriptions():
    """
    Update descriptions for lectures that haven't been updated in the last 7 days.
    Ensures execution happens within an application context.
    """
    from app import create_app

    # Create app instance and push an application context
    app = create_app()
    with app.app_context():
        _update_lecture_descriptions_impl()

@textgen_bp.route('/rewrite', methods=['POST'])
@admin_required
def rewrite_text():
    """
    Принимает JSON: { "base_text": "...", "task_type": "..." }
    Возвращает: { "result": "..." }
    """
    data = request.get_json()
    base = data.get("base_text", "").strip()
    task_type = data.get("task_type", "friendly")

    if not base:
        return jsonify({"error": "base_text is required"}), 400

    result = generate_text(base, task_type)

    if result is None:
        return jsonify({"error": "AI generation failed"}), 500

    return jsonify({"result": result})

# Initialize the scheduler when the blueprint is registered
@textgen_bp.record_once
def init_scheduler(state):
    app = state.app
    scheduler = BackgroundScheduler()

    # Schedule the update_lecture_descriptions function to run every 7 days
    # scheduler.add_job(
    #     func=update_lecture_descriptions,
    #     trigger=IntervalTrigger(days=7),
    #     id='update_lecture_descriptions',
    #     name='Update lecture descriptions every 7 days',
    #     replace_existing=True
    # )

    # Add a job to run once at startup to update any descriptions that need it
    scheduler.add_job(
        func=update_lecture_descriptions,
        trigger='date',
        run_date=datetime.datetime.now() + datetime.timedelta(days=1),
        id='initial_update_lecture_descriptions',
        name='Initial update of lecture descriptions'
    )

    scheduler.start()
    app.logger.info("Scheduler started for lecture description updates")
