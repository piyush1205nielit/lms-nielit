import uuid
import boto3
from django.conf import settings


def get_s3_client():
    return boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME)


def generate_video_upload_key(lesson_id, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp4'
    return f"raw/{lesson_id}/{uuid.uuid4().hex}.{ext}"


def generate_presigned_upload(lesson_id, filename, content_type):
    """
    Returns a presigned PUT URL scoped to a specific S3 key, valid for a short
    window. The browser uploads directly to this URL — Django never receives
    the file bytes, only issues this permission slip.
    """
    key = generate_video_upload_key(lesson_id, filename)
    client = get_s3_client()

    presigned_url = client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.AWS_RAW_VIDEO_BUCKET,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=600,   # 10 minutes to start the upload
    )

    return {'upload_url': presigned_url, 'key': key}