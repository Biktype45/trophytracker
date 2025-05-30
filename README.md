# PlayStation Trophy Tracker

A skill-based PlayStation trophy tracking platform that ranks users based on game difficulty, not just trophy quantity.

## 🎯 Overview

Unlike PSNProfiles and similar platforms, this system uses **difficulty multipliers** to prevent easy "Ratalaika" games from inflating trophy scores. Each game gets a multiplier from 1.0x (extremely easy) to 10.0x (extremely difficult).

## ✨ Key Features

- **Skill-Based Scoring**: Trophy points = Base Points × Game Difficulty Multiplier
- **20 Trophy Levels**: From "PS Noob" to "Maybe I Was The PlayStation All Along"
- **Multiple Rankings**: Global, monthly, weekly, and category-specific leaderboards
- **PlayStation API Integration**: Automatic trophy sync from PSN

## 🛠️ Tech Stack

- **Backend**: Django 4.2+, PostgreSQL
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **API**: PlayStation Trophy API v2

## 🚀 Quick Setup

1. **Clone and setup**:
```bash
git clone https://github.com/yourusername/trophy_tracker.git
cd trophy_tracker
python -m venv trophytracker
trophytracker\Scripts\activate
pip install -r requirements.txt
```

2. **Database setup**:
```sql
CREATE DATABASE trophy_tracker_dev;
CREATE USER trophy_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trophy_tracker_dev TO trophy_user;
```

3. **Environment config** (create `.env`):
```env
DB_NAME=trophy_tracker_dev
DB_USER=trophy_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your_django_secret_key
DEBUG=True
```

4. **Run**:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 📁 Project Structure

```
trophy_tracker/
├── users/          # User profiles and authentication
├── games/          # Game database and difficulty ratings
├── trophies/       # Trophy data and sync
├── rankings/       # Leaderboards and calculations
├── templates/      # HTML templates
└── static/         # CSS, JS, images
```

## 🎮 Difficulty System

| Category | Multiplier | Examples |
|----------|------------|----------|
| Extremely Easy | 1.0x | Ratalaika games |
| AAA Standard | 3.0x | Spider-Man, God of War |
| Souls-like | 6.0x | Dark Souls, Sekiro |
| Extremely Difficult | 10.0x | Super Meat Boy |

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.