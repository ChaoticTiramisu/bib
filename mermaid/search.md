```mermaid
flowchart TD
    subgraph Search_Route
        A1[Start: User accesses /search] --> B1{Is 'q' provided?}
        B1 -- Yes --> C1[Query database for books, authors, or ISBN matching 'q']
        B1 -- No --> D1[Query database for first 20 books]
        C1 --> E1[Fetch user from session]
        D1 --> E1
        E1 --> F1[Render search_result.html with results and user]
    end

    subgraph Register_Route
        A2[Start: User accesses /register] --> B2{Is method POST?}
        B2 -- Yes --> C2[Extract 'register_email' from form]
        C2 --> D2{Does email already exist in database?}
        D2 -- No --> E2[Extract other form fields: name, achternaam, password, role]
        E2 --> F2{Is email valid?}
        F2 -- Yes --> G2[Create new Gebruiker object]
        G2 --> H2[Add new user to database and commit]
        H2 --> I2[Flash success message]
        I2 --> J2[Redirect to /login]
        F2 -- No --> K2[Flash error: Invalid email]
        K2 --> L2[Render register.html with role choices]
        D2 -- Yes --> M2[Flash error: Email already in use]
        M2 --> L2
        B2 -- No --> N2[Fetch role choices from database]
        N2 --> L2[Render register.html with role choices]
    end