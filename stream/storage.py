from storages.backends.s3 import S3Storage
from django.conf import settings


class RawVideoStorage(S3Storage):
    """
    Dedicated storage backend for lesson video uploads — points at the raw
    video bucket (separate from the main static/media bucket) so that video
    files, course banners, and profile photos don't share a bucket. This
    bucket also has S3-level event notifications (Phase 2) and a lifecycle
    rule that auto-deletes objects after transcoding — neither of which
    should apply to ordinary media files.
    """
    bucket_name = settings.AWS_RAW_VIDEO_BUCKET
    region_name = settings.AWS_S3_REGION_NAME
    querystring_auth = False
    file_overwrite = False
    default_acl = None
    location = 'raw'   # objects land under raw/... inside the bucket