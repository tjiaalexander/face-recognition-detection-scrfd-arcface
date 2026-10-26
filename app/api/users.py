from __future__ import annotations

import asyncio

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import Settings
from app.database.repository import UserExistsError
from app.dependencies import get_recognizer, get_repository, get_settings, require_admin, require_model
from app.schemas.users import DeleteResponse, FrameReport, RegisterRequest, RegisterResponse, UserListOut, UserOut
from app.services.quality_check import REASON_MESSAGES, assess_face, enhance_face_image
from app.utils.images import FrameError, decode_b64_image

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


def _err(status: int, code: str, message: str, **extra):
    return HTTPException(status, {"code": code, "message": message, **extra})


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, s: Settings = Depends(get_settings),
                   repo=Depends(get_repository), recognizer=Depends(get_recognizer),
                   engine=Depends(require_model), admin: str = Depends(require_admin)):
    if not request.app.state.register_limiter.allow(admin):
        raise _err(429, "rate_limited", "Terlalu banyak permintaan registrasi. Coba lagi sebentar.")
    if not body.consent:
        raise _err(422, "consent_required", "Persetujuan pengguna wajib sebelum data wajah diambil.")
    if len(body.frames) > s.register_max_samples:
        raise _err(422, "too_many_frames", f"Maksimal {s.register_max_samples} sampel.")
    if repo.get_user(body.user_id):
        raise _err(409, "user_exists", f"ID '{body.user_id}' sudah terdaftar.")

    reports: list[FrameReport] = []
    embeddings: list[np.ndarray] = []
    qualities: list[float] = []
    for i, b64 in enumerate(body.frames):
        def add(ok: bool, reasons: list[str]):
            reports.append(FrameReport(index=i, accepted=ok, reasons=reasons,
                                       messages=[REASON_MESSAGES.get(r, r) for r in reasons]))
        try:
            img = decode_b64_image(b64, s.max_frame_bytes, s.max_frame_side)
        except FrameError as exc:
            reports.append(FrameReport(index=i, accepted=False, reasons=[exc.code], messages=[exc.message]))
            continue

        image_for_eval = img
        faces = await engine.analyze_async(img)

        if not faces:
            enhanced = enhance_face_image(img)
            if enhanced.size and not np.array_equal(enhanced, img):
                faces = await engine.analyze_async(enhanced)
                if faces:
                    image_for_eval = enhanced

        if not faces:
            add(False, ["no_face"]); continue
        if len(faces) > 1:
            add(False, ["multiple_faces"]); continue

        q = assess_face(image_for_eval, faces[0], s)
        if not q.ok and not np.array_equal(image_for_eval, img):
            q2 = assess_face(img, faces[0], s)
            if q2.ok:
                q = q2
                image_for_eval = img

        if q.ok and faces[0].embedding is not None:
            embeddings.append(faces[0].embedding)
            qualities.append(q.metrics.get("blur", 0.0))
        add(q.ok, q.reasons)

    fail = {"reports": [r.model_dump() for r in reports]}
    if len(embeddings) < s.register_min_samples:
        raise _err(422, "not_enough_samples",
                   f"Hanya {len(embeddings)} sampel berkualitas baik; minimal {s.register_min_samples}.", **fail)
    mat = np.vstack(embeddings)
    sims = mat @ mat.T
    if float(sims[np.triu_indices(len(mat), k=1)].min()) < s.register_consistency_min:
        raise _err(422, "samples_inconsistent",
                   "Sampel tampak berasal dari wajah berbeda. Pastikan hanya satu orang di depan kamera.", **fail)
    # Wajah kembar diperbolehkan; hanya ID pengguna yang harus unik.
    try:
        record = await asyncio.to_thread(repo.create_user, body.user_id, body.name, embeddings, qualities)
    except UserExistsError:
        raise _err(409, "user_exists", f"ID '{body.user_id}' sudah terdaftar.")
    await asyncio.to_thread(recognizer.reload)
    return RegisterResponse(user=UserOut(**record.__dict__), accepted_samples=len(embeddings), reports=reports)


@router.get("", response_model=UserListOut)
def list_users(search: str = Query("", max_length=100), page: int = Query(1, ge=1),
               page_size: int = Query(10, ge=1, le=100), repo=Depends(get_repository)):
    items, total = repo.list_users(search, page, page_size)
    return UserListOut(items=[UserOut(**u.__dict__) for u in items], total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, repo=Depends(get_repository)):
    user = repo.get_user(user_id)
    if not user:
        raise _err(404, "not_found", "Pengguna tidak ditemukan.")
    return UserOut(**user.__dict__)


@router.delete("/{user_id}", response_model=DeleteResponse)
def delete_user(user_id: str, repo=Depends(get_repository), recognizer=Depends(get_recognizer)):
    existed, n = repo.delete_user(user_id)
    if not existed:
        raise _err(404, "not_found", "Pengguna tidak ditemukan.")
    recognizer.reload()
    return DeleteResponse(user_id=user_id, deleted_templates=n)
