# Fixed JWT Token Creation in auth.py
# 
# This shows the specific lines that need to be changed in your auth.py file
# to fix the "Subject must be a string" error

# FIND THIS SECTION (around lines 117-120):
"""
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7)
        )
"""

# REPLACE WITH:
"""
        # Create access token
        access_token = create_access_token(
            identity=str(user.id),  # Convert user.id to string
            expires_delta=timedelta(days=7)
        )
"""

# ALSO FIND THIS SECTION (around lines 63-66 in register):
"""
        # Create access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7)
        )
"""

# REPLACE WITH:
"""
        # Create access token
        access_token = create_access_token(
            identity=str(user.id),  # Convert user.id to string
            expires_delta=timedelta(days=7)
        )
"""

# EXPLANATION:
# Flask-JWT-Extended requires the JWT subject (identity) to be a string.
# When we pass user.id (which is an integer), it causes the error:
# "Subject must be a string"
# 
# By converting user.id to str(user.id), we ensure the JWT subject is always a string.
# 
# In the onboarding routes, get_jwt_identity() will now return a string,
# so we need to convert it back to int when querying the database:
# user_id = int(get_jwt_identity())

