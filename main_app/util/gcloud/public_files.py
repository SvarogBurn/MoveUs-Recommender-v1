from main_app.util.gcloud.generate import Method, generate_signed_url

must_revalidate_headers = {
    "cache-control": "must-revalidate"
}

def generate_profile_picture_url(user_id: int):
    return generate_signed_url(
        f"profile-pictures/{user_id}",
        Method.PUT,
        headers=must_revalidate_headers
    )

def generate_event_picture_url(user_id: int):
    return generate_signed_url(
        f"event-pictures/{user_id}",
        Method.PUT,
        headers=must_revalidate_headers
    )

def generate_post_picture_url(post_id: int):
    return generate_signed_url(
        f"post-pictures/{post_id}",
        Method.PUT
    )