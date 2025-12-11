# Event Management System (EMS)

A complete event booking application built with Django 4.2 and integrated with a local AI assistant powered by Ollama.

---

## 📁 Project Structure

EMS_PROJECT/
│
├── backend/
│   ├── manage.py
│   ├── ems_core/        # project settings, URLs, base templates, chat API
│   ├── accounts/        # registration, profile, organizer flow, custom Admin portal
│   ├── events/          # events, venues, organizer analytics dashboard
│   ├── bookings/        # bookings, payments, receipts, booking rules
│   ├── customers/       # CUSTOMER entity (name, email, phone, DOB, address, etc.)
│   ├── ai/
│   │   └── services/
│   │       ├── ai_client.py      # LLM client to Ollama
│   │       ├── query_planner.py  # builds DB context for LLM
│   │       ├── action_planner.py # optional CRUD action planning (read-only in UI)
│   │       └── __init__.py
│   └── templates/       # all HTML templates (public, organizer, admin, auth)
│
├── static/              # global static files
├── media/               # uploaded files (optional)
├── scripts/             # utility scripts
├── docs/                # project docs
├── venv/                # Python virtual environment (ignored)
│
├── requirements.txt
└── README.md

---

## 🛠️ Requirements

- Python **3.12**
- Django **4.2.26**
- SQLite (default Django DB)
- Ollama installed locally  
  https://ollama.com
- Model (for AI assistant), e.g.:

```bash
ollama pull llama3.1
````

---

## ▶️ Setup Instructions

### 1. Create & activate virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
cd backend
python manage.py migrate
```

### 4. Create a Django superuser (optional, for default /admin/)

```bash
python manage.py createsuperuser
```

### 5. Create a custom Admin record (for EMS admin portal)

The EMS uses its own `ADMIN` table for the custom admin dashboard.

```bash
python manage.py shell
```

```python
from accounts.models import Admin
from django.contrib.auth.hashers import make_password

Admin.objects.create(
    username="admin1",
    password_hash=make_password("changeme123"),
    role="ADMIN",
)
exit()
```

You will then log in to the EMS admin portal with:

* URL: `/admin/login/`
* Username: `admin1`
* Password: `changeme123` (or whatever you set)

### 6. Start Ollama in another terminal

```bash
ollama serve
```

### 7. Run the dev server

```bash
python manage.py runserver
```

Visit:

* Public site: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* Custom Admin portal: [http://127.0.0.1:8000/admin/login/](http://127.0.0.1:8000/admin/login/)

---

## 🎯 Main Features

### Participants

* Register an account (captures: name, email, phone, DOB, full address, country)
* Browse all **upcoming published** events
* View **event details** including venue address and event type
* Book:

  * **Exhibitions** → information only (no booking)
  * **Conferences** → free, 1 seat per customer, capacity-limited
  * **Concerts & Sports games** → paid, capacity-limited, credit/debit card only

    * Multi-day concerts require the user to select which day they attend
* View **My Bookings** with:

  * status, ticket count, total paid
  * event and venue address
  * links to event details and booking receipts
* View **My Profile** with:

  * customer information from `CUSTOMER` (name, email, phone, DOB, address)
  * upcoming and past bookings
  * link to organizer dashboard (if approved organizer)

### Organizers

* **Become organizer** flow:

  * Logged-in user submits a request
  * Admin must approve/reject in the custom admin portal
* Once approved, organizers can:

  * Create/edit **Venues** (name, address, city, state, zip, country, capacity)
  * Create/edit **Events**, including:

    * Event type: Exhibition / Conference / Concert / Sports Game
    * Venue, title, description
    * Start & end time (validated: not in past, end > start)
    * Capacity (required for conferences and paid events)
    * Ticket price (required for Concert/Sports, must be 0 for Conference/Exhibition)
    * Status: Draft / Published / Cancelled
  * View **bookings per event** or across all their events
  * Access an **analytics dashboard** with:

    * Total events, upcoming events
    * Total bookings, tickets, and revenue
    * Per-event KPIs (bookings, tickets, revenue)
    * 6-month monthly trend (bookings/tickets/revenue)

### Custom Admin Portal (EMS Admins)

Accessible at `/admin/login/` (separate from Django’s `/admin/`).

Admins can:

* View high-level stats on the **Admin Dashboard**:

  * Events, organizers, venues, customers, bookings, pending organizer requests, admins
* Manage **Organizers**:

  * List and filter by status (Pending, Approved, Rejected)
  * Approve / reject organizer requests (updates `UserProfile.organizer`)
* Manage **Events** (CRUD via `AdminEventForm`)
* Manage **Venues** (CRUD via `AdminVenueForm`)
* Manage **Customers** (CRUD including phone, DOB, address, city, state, zip, country)
* Manage **Bookings** (CRUD via `AdminBookingForm`)
* Manage **Payments** (CRUD via `AdminPaymentForm`)
* Manage **Admin** users themselves (CRUD over the custom `ADMIN` table)

### AI Assistant

* Route: `/chat/`
* Features:

  * Natural language Q&A about:

    * Events (titles, times, venues, types)
    * Bookings (counts, totals)
    * Organizer statistics and analytics
  * Read-only access; does **not** modify the database
* Internals:

  * `ai_client.py` – HTTP client to local Ollama model
  * `query_planner.py` – inspects query and builds SQL/ORM queries to fetch context
  * `action_planner.py` – optional module for CRUD planning (not exposed to UI)

---

## 📂 Core Database Entities

* `Event`

  * `event_type` (EXHIBITION / CONFERENCE / CONCERT / SPORTS) with business rules
  * `capacity`, `ticket_price`, time window, status
* `Venue`

  * Address fields (street, city, state, zip, country), capacity
* `Organizer`

  * Linked to Django `User` (optional) + status (PENDING/APPROVED/REJECTED)
* `Customer`

  * Name, unique email, phone, DOB, full address
* `Booking`

  * Links customer ↔ event, ticket quantity, unit/total price, status, timestamps
* `Payment`

  * Links to booking + customer, amount, method (`CREDIT`/`DEBIT`), card details, paid_at
* `UserProfile`

  * Links Django `User` to `Customer` and optionally `Organizer`
* `Admin`

  * Custom EMS admin users with username, password hash, and role

---

## 🔥 Useful Commands

```bash
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

## 🚀 Notes

* Light & dark mode supported globally
* Capacity-aware booking and cancellation (cancelled bookings kept for history)
* Event time validation (no past start times, end after start)
* Booking receipts include:

  * Event and venue address
  * Participant’s full profile (including DOB and address if available)
  * Payment method and timestamp for paid events
* AI assistant is **read-only** by design for safety

```

