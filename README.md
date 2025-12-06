# Event Management System (EMS)

A complete event booking application built with Django 4.2 and integrated with a local AI assistant powered by Ollama.

---

## 📁 Project Structure

EMS_PROJECT/
│
├── backend/
│ ├── manage.py
│ ├── ems_core/ # project settings, urls, home, chat API
│ ├── accounts/ # profile, register, become organizer
│ ├── events/ # events, venues, analytics dashboard
│ ├── bookings/ # bookings, payments, receipts
│ ├── customers/ # customer object (name, email, phone)
│ ├── ai/
│ │ └── services/
│ │ ├── ai_client.py # LLM client to Ollama
│ │ ├── query_planner.py # builds DB context for LLM
│ │ ├── action_planner.py # optional CRUD action planning
│ │ └── init.py
│ └── templates/ # all HTML templates
│
├── static/ # global static files
├── media/ # uploaded files (optional)
├── scripts/ # utility scripts
├── docs/ # project docs
├── venv/ # Python virtual environment (ignored)
│
├── requirements.txt
└── README.md




---

## 🛠️ Requirements

- Python **3.12**
- Django **4.2.26**
- Ollama installed locally  
  https://ollama.com
- Model:
ollama pull llama3.1




---

## ▶️ Setup Instructions

### 1. Create & activate virtual environment

python3.12 -m venv venv
source venv/bin/activate




### 2. Install dependencies

pip install --upgrade pip
pip install -r requirements.txt




### 3. Run migrations

cd backend
python manage.py migrate




### 4. Create a superuser

python manage.py createsuperuser




### 5. Start Ollama in another terminal

ollama serve




### 6. Run the dev server

python manage.py runserver




Access the app:

http://127.0.0.1:8000/




---

## 🎯 Main Features

### Participants
- Browse all upcoming published events  
- View event details  
- Book free & paid events  
- View, print & cancel bookings  
- See profile with upcoming & past bookings  

### Organizers
- Apply to become an organizer  
- Create/edit events from UI  
- Create venues  
- View bookings per event  
- Full analytics dashboard (bookings, tickets, revenue)  

### AI Assistant
- `/chat/`
- Natural language Q&A about:
  - Events
  - Bookings
  - Organizer statistics
- Uses:
  - `ai_client.py` → talks to Ollama  
  - `query_planner.py` → builds DB context  
- Read-only (does not modify DB)  

---

## 📂 Database Entities

- `Event`
- `Venue`
- `Organizer`
- `Customer`
- `Booking`
- `Payment`
- `UserProfile` (links Django User ↔ Organizer)

---

## 🔥 Commands

python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser




---

## 🚀 Notes

- Light & dark mode supported globally  
- Capacity-aware booking  
- Cancelled bookings preserved  
- Analytics supports per-event stats + 6-month historical trend  

---



