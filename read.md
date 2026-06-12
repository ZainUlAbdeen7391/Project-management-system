# Project Management System

A comprehensive project management application built with FastAPI.

## Features

- User authentication and authorization
- Project management
- Task assignment and tracking
- Comments and collaboration
- File attachments
- Role-based access control (RBAC)
- Activity logging

## Technology Stack

- **Backend**: FastAPI
- **Database**: MySQL
- **ORM**: aiomysql (async)
- **Authentication**: JWT with python-jose
- **Password Hashing**: bcrypt
- **Email**: fastapi-mail
- **Encryption**: cryptography (AESGCM)

## Project Structure

```
Project Management System/
├── configurations/          # Configuration files (database, mail)
├── repositories/           # Database access layer
├── Routers/               # API endpoints
├── schemas/               # Pydantic data models
├── utilities/             # Utility functions (security, dependencies)
├── uploads/               # User uploaded files
├── myenv/                 # Python virtual environment
├── main.py                # Application entry point
└── requirements.txt       # Python dependencies
```

## Installation

### Prerequisites
- Python 3.10+
- MySQL 5.7+

### Setup

1. Create virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database connection in `.env` or `configurations/database.py`

4. Run the application:
```bash
python -m uvicorn main:app --reload
```

## API Documentation

Once the application is running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - User login
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password

### Projects
- `GET /projects` - List all projects
- `POST /projects` - Create new project
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project

### Tasks
- `GET /tasks` - List all tasks
- `POST /tasks` - Create new task
- `GET /tasks/{id}` - Get task details
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

### Comments
- `GET /comments` - List comments
- `POST /comments` - Create comment
- `PUT /comments/{id}` - Update comment
- `DELETE /comments/{id}` - Delete comment

### Clients
- `GET /clients` - List clients
- `POST /clients` - Create client
- `GET /clients/{id}` - Get client details
- `PUT /clients/{id}` - Update client
- `DELETE /clients/{id}` - Delete client

### Attachments
- `GET /attachments/{entity_type}/{entity_id}` - List attachments
- `POST /attachments` - Upload file
- `DELETE /attachments/{id}` - Delete attachment

## Database Schema

The application uses the following main tables:
- `tbl_users` - User information
- `tbl_projects` - Project data
- `tbl_tasks` - Task information
- `tbl_comments` - Comments and discussions
- `tbl_clients` - Client information
- `tbl_attachments` - File attachments
- `tbl_roles` - User roles
- `tbl_module_role_permissions` - Permission mappings

## Development

### Running Tests
```bash
pytest
```

### Code Style
The project follows PEP 8 guidelines.

## License

All rights reserved.

## Support

For issues or questions, please contact the development team.
