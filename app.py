import streamlit as st
import io
import re
import os
from typing import List, Dict

# ----------------------
# Page Configuration
# ----------------------
st.set_page_config(
    page_title="Pak Textbook AI Helper",
    page_icon="📖",
    layout="wide"
)

# ----------------------
# Groq API Setup
# ----------------------
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Get API key from Streamlit Secrets (Advanced Options)
groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

if GROQ_AVAILABLE and groq_api_key:
    client = Groq(api_key=groq_api_key)
    USE_GROQ = True
else:
    USE_GROQ = False

# ----------------------
# Session State Init
# ----------------------
if "chapter_text" not in st.session_state:
    st.session_state.chapter_text = ""
if "questions" not in st.session_state:
    st.session_state.questions = []
if "language" not in st.session_state:
    st.session_state.language = "English"

# ----------------------
# Helper Functions
# ----------------------

def extract_text_from_file(uploaded_file) -> str:
    """Extract text from .txt, .pdf, .docx files safely"""
    if uploaded_file is None:
        return ""
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".txt"):
            return uploaded_file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        else:
            st.warning(f"❌ Unsupported file type: {filename}")
            return ""
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
        return ""


def clean_text(text: str) -> str:
    """Clean and normalize chapter text"""
    return re.sub(r'\s+', ' ', text).strip()


def generate_questions_with_groq(chapter_text: str, lang: str, num_mcq=3, num_short=2, num_long=1) -> List[Dict]:
    """Use Groq LLM to generate high-quality questions"""
    lang_prompt = {
        "English": "Respond in English.",
        "Urdu": "Respond in Urdu script.",
        "Roman Urdu": "Respond in Roman Urdu."
    }[lang]

    prompt = f"""
You are an exam question generator for Pakistani Matriculation and Intermediate students.

{lang_prompt}

Below is textbook chapter content. Generate:
- {num_mcq} Multiple Choice Questions (MCQs)
- {num_short} Short Answer Questions
- {num_long} Long Answer Question

Return output in JSON format like this:
[
  {{
    "type": "MCQ",
    "question": "Your question here",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "Correct option text",
    "explanation": "Explain why in {lang}"
  }},
  {{
    "type": "Short Question",
    "question": "Question text",
    "correct_answer": "Correct answer from chapter",
    "explanation": "Explanation in {lang}"
  }}
]

CHAPTER CONTENT:
{chapter_text[:12000]}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=3500
        )
        content = response.choices[0].message.content.strip()

        # Extract JSON safely
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())
        else:
            st.warning("⚠️ Could not parse AI response. Using built-in generator instead.")
            return generate_questions_fallback(chapter_text, lang, num_mcq, num_short, num_long)
    except Exception as e:
        st.warning(f"⚠️ Groq unavailable: {str(e)}. Using built-in generator instead.")
        return generate_questions_fallback(chapter_text, lang, num_mcq, num_short, num_long)


def generate_questions_fallback(chapter_text: str, lang: str, num_mcq=3, num_short=2, num_long=1) -> List[Dict]:
    """Fallback question generator when Groq is unavailable"""
    sentences = [s.strip() for s in re.split(r'[.!?]+', chapter_text) if len(s.strip()) > 20]
    questions = []
    expl_prefix = {
        "English": "From the chapter: ",
        "Urdu": "باب سے: ",
        "Roman Urdu": "Bab se: "
    }[lang]

    for i in range(min(num_mcq, len(sentences))):
        sent = sentences[i]
        words = sent.split()
        if len(words) > 4:
            blank_idx = len(words) // 3
            correct = words[blank_idx]
            words[blank_idx] = "_______"
            q_text = " ".join(words)
            questions.append({
                "type": "MCQ",
                "question": q_text,
                "options": [correct, words[0], words[-1], words[len(words)//2]],
                "correct_answer": correct,
                "explanation": expl_prefix + sent
            })

    for i in range(num_short):
        idx = min(i + num_mcq, len(sentences)-1)
        if idx < len(sentences):
            sent = sentences[idx]
            q_text = sent[:min(60, len(sent))] + "..."
            questions.append({
                "type": "Short Question",
                "question": "Explain briefly: " + q_text,
                "correct_answer": sent,
                "explanation": expl_prefix + sent
            })

    if sentences:
        topic = sentences[0][:min(70, len(sentences[0]))]
        summary = " ".join(sentences[:min(4, len(sentences))])
        questions.append({
            "type": "Long Question",
            "question": "Explain in detail: " + topic + "...",
            "correct_answer": summary,
            "explanation": expl_prefix + summary
        })
    return questions


def check_answer(user_answer: str, correct_answer: str, lang: str) -> Dict:
    """Compare answer and return feedback in selected language"""
    if not user_answer.strip():
        return {
            "status": "empty",
            "message": {
                "English": "⚠️ Please enter your answer.",
                "Urdu": "⚠️ براہ کرم اپنا جواب درج کریں۔",
                "Roman Urdu": "⚠️ Meharbani karke apna jawab dein."
            }[lang]
        }

    user_words = set(user_answer.lower().split())
    correct_words = set(correct_answer.lower().split())
    common = user_words & correct_words
    score = len(common) / max(len(correct_words), 1)

    if score >= 0.7:
        status = "correct"
        msg = {
            "English": "✅ Excellent! Your answer matches the textbook.",
            "Urdu": "✅ بہت اچھا! آپ کا جواب درسی کتاب کے مطابق ہے۔",
            "Roman Urdu": "✅ Bahot acha! Apka jawab darsiy kitab ke mutabiq hai."
        }[lang]
    elif score >= 0.35:
        status = "partial"
        msg = {
            "English": "⚠️ Good effort! Some points are missing.",
            "Urdu": "⚠️ اچھی کوشش! کچھ نکات کی کمی ہے۔",
            "Roman Urdu": "⚠️ Achhi koshish! Kuch cheezein reh gayi hain."
        }[lang]
    else:
        status = "incorrect"
        msg = {
            "English": "❌ Let's review. Please check the chapter again.",
            "Urdu": "❌ جائزہ لیں۔ براہ کرم باب کو دوبارہ پڑھیں۔",
            "Roman Urdu": "❌ Jaiza lein. Meharbani karke bab dobara parhein."
        }[lang]

    return {
        "status": status,
        "score": round(score * 100),
        "message": msg
    }

# ----------------------
# UI Interface
# ----------------------

st.title("📖 Pakistan Textbook AI Helper")
st.subheader("Prepare for Matric & Inter Exams — From Your Own Textbook")
st.divider()

# --- Language Selection ---
st.sidebar.header("⚙️ Settings")
language = st.sidebar.radio(
    "Select Language for Explanations:",
    ["English", "Urdu", "Roman Urdu"],
    index=0
)
st.session_state.language = language

# --- Groq Status ---
with st.sidebar:
    st.divider()
    if USE_GROQ:
        st.success("✅ Groq API Connected")
    else:
        st.warning("⚠️ Groq API Key not set — using basic mode")
        st.info("💡 Add GROQ_API_KEY in Streamlit Settings → Secrets")

# --- Step 1: Upload / Paste ---
st.header("📤 Step 1 — Add Your Chapter")
tab1, tab2 = st.tabs(["📁 Upload File", "✏️ Paste Text"])

with tab1:
    uploaded_file = st.file_uploader(
        "Upload textbook chapter",
        type=["txt", "pdf", "docx"],
        help="Supported formats: .txt, .pdf, .docx"
    )
    if uploaded_file:
        text = extract_text_from_file(uploaded_file)
        if text:
            st.session_state.chapter_text = clean_text(text)
            st.success(f"✅ Loaded! ({len(st.session_state.chapter_text)} characters)")

with tab2:
    pasted = st.text_area(
        "Paste chapter text here:",
        height=200,
        placeholder="Copy your textbook chapter and paste here..."
    )
    if st.button("📝 Save Text") and pasted.strip():
        st.session_state.chapter_text = clean_text(pasted)
        st.success(f"✅ Saved! ({len(st.session_state.chapter_text)} characters)")

# --- Step 2: Generate Questions ---
if st.session_state.chapter_text:
    st.divider()
    st.header("📝 Step 2 — Create Practice Questions")
    col1, col2, col3 = st.columns(3)
    with col1: mcq_count = st.slider("Number of MCQs", 1, 5, 3)
    with col2: short_count = st.slider("Short Questions", 1, 4, 2)
    with col3: long_count = st.slider("Long Questions", 1, 2, 1)

    gen_mode = "AI-Powered (Groq)" if USE_GROQ else "Basic Mode"
    st.info(f"🔄 Generation Mode: {gen_mode}")

    if st.button("✨ Generate Questions", type="primary"):
        with st.spinner("Generating questions from your chapter..."):
            if USE_GROQ:
                st.session_state.questions = generate_questions_with_groq(
                    st.session_state.chapter_text, language,
                    mcq_count, short_count, long_count
                )
            else:
                st.session_state.questions = generate_questions_fallback(
                    st.session_state.chapter_text, language,
                    mcq_count, short_count, long_count
                )
            st.success(f"✅ {len(st.session_state.questions)} questions generated!")

# --- Step 3: Practice ---
if st.session_state.questions:
    st.divider()
    st.header("✍️ Step 3 — Practice & Check Answers")

    for idx, q in enumerate(st.session_state.questions, 1):
        with st.expander(f"Q{idx}: {q['type']}", expanded=True):
            st.subheader(q["question"])

            if q["type"] == "MCQ":
                user_ans = st.radio("Select your answer:", q.get("options", []), key=f"q{idx}_opt")
            else:
                height = 110 if q["type"] == "Long Question" else 70
                user_ans = st.text_area("Your Answer:", height=height, key=f"q{idx}_ans")

            if st.button(f"✅ Check Answer #{idx}", key=f"check{idx}"):
                result = check_answer(user_ans, q["correct_answer"], language)
                st.markdown(result["message"])
                if result["status"] != "correct":
                    with st.container(border=True):
                        st.info("📖 **Correct Answer from Chapter:**")
                        st.write(q["correct_answer"])
                        st.caption(q.get("explanation", ""))
                else:
                    st.success("🎉 Well done!")

# --- Reset ---
st.sidebar.divider()
if st.sidebar.button("🔄 Reset All"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# --- Footer ---
st.divider()
st.caption("📚 For Pakistani Matric & Intermediate Students • Answers from YOUR textbook")
