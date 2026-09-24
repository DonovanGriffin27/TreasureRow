
# The Vault – Backend (Flask)

This folder contains the backend implementation for The Vault marketplace. The backend manages data storage, business rules, authentication, and API endpoints.

---

## Architecture Overview

The backend follows a layered architecture to separate responsibilities and maintain scalability.

Controllers handle HTTP requests and responses.
Services contain business logic and system rules.
Models define database structure and relationships.
Utils provide shared helper functionality.

Controllers do not contain business logic.
Services do not handle HTTP requests directly.

---

## Folder Breakdown

### app.py

Initializes the Flask application and registers Blueprints. This is the entry point of the backend.

### config/

Contains application configuration and environment setup.

Responsibilities include:

* Database connection configuration
* Secret keys
* JWT configuration
* AWS configuration
* Environment-specific settings

---

### controllers/

Defines API endpoints using Flask Blueprints.

Responsibilities include:

* Defining routes (GET, POST, PUT, DELETE)
* Parsing request data
* Performing basic validation
* Calling service-layer functions
* Returning structured JSON responses

Controllers act as the interface between the frontend and backend logic.

---

### models/

Defines the relational database schema using ORM models.

Core models include:

* User
* Storefront
* Listing
* Transaction

Models define:

* Table columns
* Primary and foreign keys
* Relationships between tables
* Data constraints

Models describe what data looks like and how tables relate to each other.

---

### services/

Contains business logic and system rules.

Responsibilities include:

* Enforcing ownership and role-based permissions
* Validating business workflows
* Coordinating multi-step processes
* Interacting with database models
* Maintaining data integrity

Examples:

* Ensuring only the owner can edit their storefront
* Preventing users from modifying other users’ listings
* Enforcing fulfillment rules (IN_STOCK vs PREORDER)
* Soft deleting listings instead of permanently removing records
* Allowing admin moderation

All permission enforcement and core system rules live in this layer.

---

### utils/

Reusable helper functions used across the backend.

Examples include:

* Password hashing
* JWT token creation and validation
* Role-check decorators
* Input validation helpers
* S3 upload helpers
* Custom error handling

Utilities support the system but do not contain business workflows.

---

### tests/

Contains automated tests for validating backend functionality.

Test coverage may include:

* Authentication
* Storefront creation
* Listing ownership enforcement
* Transaction logic

Tests help ensure that core marketplace functionality remains stable.

---

## Ownership and Role Model

The system enforces role-based access control.

Roles:

* Owner manages their own storefront and listings.
* Admin oversees all storefronts and listings.

Ownership enforcement ensures:

* A storefront can only be updated by its owner or an admin.
* A listing can only be modified by the owner of the storefront it belongs to, unless performed by an admin.


