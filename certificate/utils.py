from django.core.cache import cache
import qrcode
from io import BytesIO


def get_or_generate_qr_code(certificate_number, verification_url):
    """Get QR code from cache or generate new one. Cache expires after 7 days."""
    cache_key = f'qr_code_{certificate_number}'
    qr_data = cache.get(cache_key)

    if not qr_data:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        qr_data = buffer.getvalue()
        buffer.close()

        cache.set(cache_key, qr_data, 60 * 60 * 24 * 7)

    return qr_data


CERTIFICATE_PLACEHOLDER_HELP = (
    "Available placeholders in body text fields: {student_name}, {course_name}, "
    "{start_date}, {end_date}, {registration_number}, {institute_name}, {duration}"
)