import uuid
import boto3
from django.conf import settings
import json
from functools import lru_cache
import datetime

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key


@lru_cache(maxsize=1)
def get_cloudfront_private_key():
    """
    Fetches the CloudFront signing private key from Secrets Manager once,
    then caches it in memory for the lifetime of the process — avoids
    hitting Secrets Manager on every single video playback request.
    """
    client = boto3.client('secretsmanager', region_name=settings.AWS_S3_REGION_NAME)
    response = client.get_secret_value(SecretId=settings.CLOUDFRONT_SECRET_NAME)
    return response['SecretString'].encode('utf-8')


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


@lru_cache(maxsize=1)
def get_cloudfront_private_key():
    """
    Fetches the CloudFront signing private key from Secrets Manager once,
    then caches it in memory for the lifetime of the process — avoids
    hitting Secrets Manager on every single video playback request.
    """
    client = boto3.client('secretsmanager', region_name=settings.AWS_S3_REGION_NAME)
    response = client.get_secret_value(SecretId=settings.CLOUDFRONT_SECRET_NAME)
    return response['SecretString'].encode('utf-8')


def _rsa_signer(message):
    private_key = load_pem_private_key(get_cloudfront_private_key(), password=None)
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def generate_signed_cookies(resource_path_prefix):
    """
    Generates CloudFront signed cookies granting access to everything under
    the given path prefix, expiring after CLOUDFRONT_SIGNED_URL_EXPIRY_SECONDS.

    resource_path_prefix example: 'hls/lessons/<lesson_id>/*'
    """
    cloudfront_signer = CloudFrontSigner(settings.CLOUDFRONT_KEY_PAIR_ID, _rsa_signer)

    expire_time = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=settings.CLOUDFRONT_SIGNED_URL_EXPIRY_SECONDS
    )

    resource_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{resource_path_prefix}"

    policy = cloudfront_signer.build_policy(resource_url, expire_time)
    policy_bytes = policy.encode('utf-8')

    signature = _rsa_signer(policy_bytes)

    import base64
    def cf_base64(data):
        return base64.b64encode(data).replace(b'+', b'-').replace(b'=', b'_').replace(b'/', b'~').decode('utf-8')

    return {
        'CloudFront-Policy': cf_base64(policy_bytes),
        'CloudFront-Signature': cf_base64(signature),
        'CloudFront-Key-Pair-Id': settings.CLOUDFRONT_KEY_PAIR_ID,
    }