import json
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from app import db
from app.models import Conversation, Message, GeneratedImage
from app.utils import login_required, get_current_user
from app.groq_engine import chat_with_faithguide, generate_christian_content
from app.safety import classify_input, get_sensitive_preamble, filter_output
from app.image_gen import generate_christian_image, suggest_christian_image_prompts
from config import Config

chat_bp = Blueprint('chat', __name__)


# ── Main chat page ────────────────────────────────────────────────────────────
@chat_bp.route('/chat', methods=['GET'])
@login_required
def index():
    user          = get_current_user()
    conversations = (Conversation.query
                     .filter_by(user_id=user.id)
                     .order_by(Conversation.updated_at.desc())
                     .limit(20).all())
    return render_template('chat/index.html',
                           user          = user,
                           conversations = conversations)


# ── New conversation ──────────────────────────────────────────────────────────
@chat_bp.route('/chat/new', methods=['POST'])
@login_required
def new_conversation():
    user = get_current_user()
    conv = Conversation(user_id=user.id, title='New Conversation')
    db.session.add(conv)
    db.session.commit()
    return redirect(url_for('chat.conversation', conv_id=conv.id))


# ── Load conversation ─────────────────────────────────────────────────────────
@chat_bp.route('/chat/<int:conv_id>')
@login_required
def conversation(conv_id):
    user = get_current_user()
    conv = Conversation.query.filter_by(
        id      = conv_id,
        user_id = user.id
    ).first_or_404()

    conversations = (Conversation.query
                     .filter_by(user_id=user.id)
                     .order_by(Conversation.updated_at.desc())
                     .limit(20).all())

    return render_template('chat/index.html',
                           user          = user,
                           conversations = conversations,
                           active_conv   = conv,
                           messages      = conv.messages)


# ── Send message ──────────────────────────────────────────────────────────────
@chat_bp.route('/chat/<int:conv_id>/send', methods=['POST'])
@login_required
def send_message(conv_id):
    user = get_current_user()
    conv = Conversation.query.filter_by(
        id      = conv_id,
        user_id = user.id
    ).first_or_404()

    user_message = request.form.get('message', '').strip()
    if not user_message:
        return redirect(url_for('chat.conversation', conv_id=conv_id))

    # ── Step 1: Safety classification ────────────────────────────────────────
    safety = classify_input(user_message)

    if not safety["safe"]:
        user_msg = Message(
            conversation_id = conv_id,
            role            = 'user',
            content         = user_message
        )
        db.session.add(user_msg)

        blocked_msg = Message(
            conversation_id = conv_id,
            role            = 'assistant',
            content         = (
                "I'm sorry, I cannot process that request. "
                f"{safety['reason']}"
            )
        )
        db.session.add(blocked_msg)
        db.session.commit()
        return redirect(url_for('chat.conversation', conv_id=conv_id))

    # ── Step 2: Build conversation history ───────────────────────────────────
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
    ]

    # ── Step 3: Preamble for sensitive topics ─────────────────────────────────
    preamble = get_sensitive_preamble(safety["category"], user_message)

    # ── Step 4: Call Groq AI engine ───────────────────────────────────────────
    denomination = session.get('denomination', 'Protestant (General)')
    result       = chat_with_faithguide(
        user_message         = user_message,
        conversation_history = history,
        denomination         = denomination
    )

    ai_response = preamble + result["response"]

    # ── Step 5: Output safety filter ─────────────────────────────────────────
    output_check   = filter_output(ai_response)
    final_response = output_check["response"]

    # ── Step 6: Save user message ─────────────────────────────────────────────
    user_msg = Message(
        conversation_id = conv_id,
        role            = 'user',
        content         = user_message
    )
    db.session.add(user_msg)

    # ── Step 7: Save AI message with verified verses ──────────────────────────
    verses_list = [v["reference"] for v in result["verses_used"]]
    verses_json = json.dumps(verses_list)

    ai_msg = Message(
        conversation_id = conv_id,
        role            = 'assistant',
        content         = final_response,
        verses_used     = verses_json
    )
    db.session.add(ai_msg)

    # ── Step 8: Auto-title first message ──────────────────────────────────────
    if conv.title == 'New Conversation' and len(conv.messages) == 0:
        conv.title = (
            user_message[:60] +
            ('...' if len(user_message) > 60 else '')
        )

    db.session.commit()
    return redirect(url_for('chat.conversation', conv_id=conv_id))


# ── Delete conversation ───────────────────────────────────────────────────────
@chat_bp.route('/chat/<int:conv_id>/delete', methods=['POST'])
@login_required
def delete_conversation(conv_id):
    user = get_current_user()
    conv = Conversation.query.filter_by(
        id      = conv_id,
        user_id = user.id
    ).first_or_404()
    db.session.delete(conv)
    db.session.commit()
    return redirect(url_for('chat.index'))


# ── Image generation page ─────────────────────────────────────────────────────
@chat_bp.route('/images', methods=['GET'])
@login_required
def image_page():
    user      = get_current_user()
    prompts   = suggest_christian_image_prompts()
    my_images = (GeneratedImage.query
                 .filter_by(user_id=user.id)
                 .order_by(GeneratedImage.created_at.desc())
                 .limit(12).all())
    return render_template('chat/image.html',
                           user              = user,
                           suggested_prompts = prompts,
                           my_images         = my_images)


# ── Generate image POST ───────────────────────────────────────────────────────
@chat_bp.route('/images/generate', methods=['POST'])
@login_required
def generate_image():
    user   = get_current_user()
    prompt = request.form.get('prompt', '').strip()

    if not prompt:
        flash('Please enter an image prompt.', 'danger')
        return redirect(url_for('chat.image_page'))

    result = generate_christian_image(prompt, user_id=user.id)

    if not result["success"]:
        flash(f'Image generation failed: {result["error"]}', 'danger')
        return redirect(url_for('chat.image_page'))

    # Store result in session for redirect
    session['last_image_url']    = result["image_url"]
    session['last_image_prompt'] = prompt
    session['last_safe_prompt']  = result["safe_prompt"]

    return redirect(url_for('chat.image_result'))


# ── Image result page ─────────────────────────────────────────────────────────
@chat_bp.route('/images/result')
@login_required
def image_result():
    image_url   = session.pop('last_image_url',    None)
    prompt      = session.pop('last_image_prompt', '')
    safe_prompt = session.pop('last_safe_prompt',  '')

    if not image_url:
        flash('No image found. Please generate one first.', 'warning')
        return redirect(url_for('chat.image_page'))

    user = get_current_user()
    return render_template('chat/image_result.html',
                           user        = user,
                           prompt      = prompt,
                           image_url   = image_url,
                           safe_prompt = safe_prompt)


# ── Content generator page ────────────────────────────────────────────────────
@chat_bp.route('/content', methods=['GET'])
@login_required
def content_page():
    user = get_current_user()
    return render_template('chat/content.html', user=user)


# ── Generate content POST ─────────────────────────────────────────────────────
@chat_bp.route('/content/generate', methods=['POST'])
@login_required
def generate_content():
    user         = get_current_user()
    content_type = request.form.get('content_type', 'devotional')
    topic        = request.form.get('topic', '').strip()
    denomination = session.get('denomination', 'Protestant (General)')

    if not topic:
        flash('Please enter a topic.', 'danger')
        return redirect(url_for('chat.content_page'))

    result = generate_christian_content(
        content_type = content_type,
        topic        = topic,
        denomination = denomination
    )

    if result["error"]:
        flash(f'Generation failed: {result["error"]}', 'danger')
        return redirect(url_for('chat.content_page'))

    return render_template('chat/content_result.html',
                           user         = user,
                           result       = result,
                           content_type = content_type,
                           topic        = topic)