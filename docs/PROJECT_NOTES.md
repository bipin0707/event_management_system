

# 📄 **Project Notes (Developer Insights & Internal Documentation)**

This document contains internal notes, decisions, and explanations about how I built the **Event Management System (EMS)**. These notes are intentionally informal and technical — they are meant for developers or anyone maintaining or reviewing the project codebase.

---

# ⚙️ **1. Project Overview (Developer Viewpoint)**

The EMS was built with the goal of creating a clean, modular, maintainable Django application that supports:

* Multiple event types
* Booking and payment logic
* Organizer and admin workflows
* Local AI chatbot integration
* Cross-platform setup (macOS + Windows)

The design strictly follows the conceptual ERD, but includes extra implementation tables and fields where required.

---

# 🧱 **2. Project Structure Notes**

```
backend/
├── ems_core/        # Core project settings, URLs, AI endpoint
├── accounts/        # User profiles, authentication extensions
├── events/          # Event and venue management
├── bookings/        # Booking + Payment logic
├── templates/       # Shared HTML templates
└── static/          # Static files (CSS/JS)
```

### Why this structure?

I separated each functional domain into its own Django app to:

* Make the system easier to maintain
* Support modular development
* Keep each app focused on its own data and logic
* Follow Django best practices

---

# 🧩 **3. Key Implementation Decisions**

### ✔️ Use of SQLite

Chosen because it’s lightweight and perfect for local development + academic projects.
Can be swapped for PostgreSQL easily.

### ✔️ Events split into four types

* Exhibition → no booking
* Conference → free booking
* Concert/Sports → paid
  This required condition-based logic in both models and views.

### ✔️ Added fields not in ERD

(e.g., `description`, `ticket_price`, organizer-to-user links)
These were necessary for practical UI/UX and authentication.

### ✔️ Use of Django’s built-in auth

Instead of building custom users, I extended Django’s user model through `accounts_userprofile`.

### ✔️ UserProfile table

This maps:

* Django user → Customer
* Django user → Organizer

---

# 🤖 **4. AI Integration Notes (Ollama + Llama 3.1)**

### How it works:

* AI requests go to `services/ai_client.py`
* That module sends JSON to:

  ```
  http://localhost:11434/api/chat
  ```
* Llama 3.1 provides natural language responses
* Django formats and renders them in the UI

### Why local AI?

* Works offline
* No API costs
* More secure (no data leaves machine)

### Common pitfalls noticed:

* Ollama must be running before making requests
* Windows users must explicitly allow Ollama through firewall
* The AI sometimes needs precise prompts for best results

---

# 🔐 **5. Security Decisions**

* Password hashing uses Django defaults (PBKDF2)
* Card details stored *masked only*
* Booking limits enforced server-side
* AI inputs sanitized before sending to model
* Admin panel restricted to superusers only
* Organizer cannot access or modify admin-only data

---

# 🧪 **6. Testing Notes**

I tested:

* Booking rules
* Capacity enforcement
* Payment logic
* Event publishing workflow
* AI response flow
* Organizer permissions

I did manual scenario-based testing rather than automated test suites, due to time constraints of the academic assignment.

---

# 🧭 **7. Known Issues (Technical)**

* Venue conflict detection (overlapping events) not implemented
* Real payment gateway not included
* Seat reservation does not support seat maps
* No email/SMS notifications
* AI cannot directly query database

None of these break the system, but they are important to document.

---

# 🚀 **8. Future Enhancements (From a Developer’s Perspective)**

* Switch from SQLite → PostgreSQL (better concurrency)
* Add Celery for background tasks (e.g., sending emails)
* Add WebSockets for real-time seat availability
* Expand AI features to auto-generate event summaries
* Build REST API endpoints for mobile app integration
* Add role-based dashboards (Admin, Organizer, Student)

---

# 📌 **9. Deployment Notes**

If deploying for real-world use:

* Replace SQLite with PostgreSQL
* Use Gunicorn + Nginx
* Enable HTTPS
* Configure environment variables for secrets
* Use Redis for caching AI responses
* Use Docker for consistent environments

---

# 📝 **10. Personal Notes (Optional, But Great for Academic Insight)**

These sections help demonstrate your personal involvement and architectural thinking.

### What I learned:

* Importance of conceptual vs. physical database design
* Clean separation of logic using multiple Django apps
* Handling different event types with unique rules
* Integrating locally hosted LLMs in a web system
* Ensuring consistent business logic across UI and backend

### Challenges I faced:

* Getting Ollama to run consistently on Windows
* Ensuring AI does not interfere with or break business rules
* Managing organizer/user roles cleanly
* Testing capacity rules under multiple scenarios

---

# 🎉 End of Project Notes

