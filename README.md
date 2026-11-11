# 📖 Pakistan Textbook AI Helper

> AI-powered exam preparation app for **Matriculation & Intermediate students in Pakistan**. Students upload a chapter from their textbook, and the app generates practice questions, checks answers, and provides explanations — in **English, Urdu, or Roman Urdu**.

---

## ✨ Features

- 📤 **Upload or paste** textbook chapters (.txt, .pdf, .docx)
- 🤖 **AI Question Generation** — powered by Groq LLM
- 📝 **3 question types**: MCQs, Short Questions, Long Questions
- ✅ **Instant Answer Checking** — compares responses with chapter content
- 🗣️ **3 Languages**: English • Urdu • Roman Urdu
- 🔒 **Privacy First** — all content stays with the student
- 🇵🇰 Built for Pakistani curriculum

---

## 🚀 How to Run

### Option A — Streamlit Cloud (Recommended)
1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) → Connect your GitHub repo
3. **Add your Groq API Key:**
   - Go to App Settings → Secrets
   - Click "Add a secret"
   - **Key:** `GROQ_API_KEY`
   - **Value:** `your-groq-api-key-here`
4. Click Save → Your app is live! 🎉

### Option B — Local Machine
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Groq API key
# Windows: set GROQ_API_KEY=your_key_here
# Mac/Linux: export GROQ_API_KEY=your_key_here

# 3. Run the app
streamlit run app.py
