# Django Newsletter Project

This project is a simple email newsletter web application built with Django. It allows users to subscribe with their email address and for admins to send newsletters to the list of subscribers.

## Features

- **Email Subscription:** Users can subscribe to your newsletter.
- **Admin Campaign Sender:** Admins can create and send newsletters to all subscribers.
- **SQLite Database:** Uses SQLite by default for quick setup and development.
- **Email Sending:** Configured for Gmail SMTP (can be changed).

## Getting Started

### Requirements

- Python 3.8+
- Django 4.2+
- A Gmail account or an SMTP server for sending emails

### Setup

1. **Clone the Repository**

   ```bash
   git clone <your-repo-url>
   cd <project-folder>
   ```

2. **Create and Activate a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install django
   ```

4. **Migrate Database**

   ```bash
   python manage.py migrate
   ```

5. **Configure Email Settings**

   Open `newsletter_project/settings.py` and set your email credentials:

   ```python
   EMAIL_HOST_USER = "your-email@gmail.com"
   EMAIL_HOST_PASSWORD = "your-app-password"
   ```

   > **Note:** For Gmail, you may need to [generate an app password](https://support.google.com/accounts/answer/185833).

6. **Run the Development Server**

   ```bash
   python manage.py runserver
   ```

## Usage

- Visit `http://localhost:8000/subscribe/` to subscribe to the newsletter.
- Admins can access `/admin/` to manage newsletter campaigns or use the `/send/<campaign_id>/` endpoint to send a campaign.

## File Structure

```
newsletter_project/
├── newsletter/
│   ├── templates/newsletter/
│   │   └── success.html
│   ├── views.py
│   ├── urls.py
│   └── ...
├── newsletter_project/
│   ├── settings.py
│   └── ...
├── db.sqlite3
└── manage.py
```

## Customization

- **SMTP Provider:** Change the email backend settings in `settings.py` if you're not using Gmail.
- **Templates:** You can improve or customize the HTML templates in `newsletter/templates/newsletter/`.

## Security

- **Never commit real credentials.** Use environment variables or a `.env` file and [`python-dotenv`](https://pypi.org/project/python-dotenv/) for production.
- The project is for demonstration. For production, set `DEBUG = False` and properly secure your secret keys and credentials.

## License

This project is open-source and free to use under the MIT License.
