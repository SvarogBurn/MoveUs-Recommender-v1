from main_app.util.gcloud.generate import generate_signed_url, Method

def generate_profile_picture_url(user_id: int):
    return generate_signed_url(
        f"profile-pictures/{user_id}",
        Method.PUT
    )

def generate_event_picture_url(user_id: int):
    return generate_signed_url(
        f"event-pictures/{user_id}",
        Method.PUT
    )

def generate_post_picture_url(post_id: int):
    return generate_signed_url(
        f"post-pictures/{post_id}",
        Method.PUT
    )