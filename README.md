# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

3. Set admin approval credentials using environment variables before launching the app:

   ```bash
   export ADMIN_USER=admin
   export ADMIN_PASSWORD="Admin@3453"
   ```

   The app also defaults to `Admin@3453` if `ADMIN_PASSWORD` is not set.

4. Optional: connect to MongoDB instead of local JSON storage by setting:

   ```bash
   export MONGO_URI="your_mongodb_connection_string"
   export MONGO_DB="your_database_name"
   ```

   If you want to use username/password auth instead of X.509, either put the credentials in the URI or set:

   ```bash
   export MONGO_USERNAME="your_user"
   export MONGO_PASSWORD="your_password"
   export MONGO_AUTH_SOURCE="admin"  # optional, if needed
   ```

   Then run:

   ```bash
   streamlit run streamlit_app.py
   ```
