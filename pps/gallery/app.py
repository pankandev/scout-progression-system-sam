from core import JSONResponse, HTTPEvent
from core.aws.errors import HTTPError
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService


def get_avatar(event: HTTPEvent) -> JSONResponse:
    sub = event.params["sub"]
    avatar = BeneficiariesService.get_avatar(sub)
    return JSONResponse(avatar)


def update_avatar(event: HTTPEvent) -> JSONResponse:
    sub = event.params["sub"]
    if event.authorizer.sub != sub:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Only the avatar owner can update the avatar")
    new_avatar = BeneficiariesService.update_avatar(event.authorizer.sub, event.json)
    return JSONResponse({'avatar': new_avatar})


router = Router()
router.get('/api/beneficiaries/{sub}/avatar/', get_avatar)
router.put('/api/beneficiaries/{sub}/avatar/', update_avatar)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
