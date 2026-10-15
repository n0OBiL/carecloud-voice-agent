from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.database import get_db
from app.models import CallLog
from app.voice.tools import end_call, lookup_patient, save_patient, update_patient, validate_field

router = APIRouter(prefix="/voice", tags=["voice"])


def _dispatch_tool(tool_name: str, tool_inputs: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "lookup_patient":
        return lookup_patient(tool_inputs)
    if tool_name == "validate_field":
        return validate_field(tool_inputs)
    if tool_name == "save_patient":
        return save_patient(tool_inputs)
    if tool_name == "update_patient":
        return update_patient(tool_inputs)
    if tool_name == "end_call":
        return end_call(tool_inputs)

    raise HTTPException(status_code=400, detail=f"Unsupported tool: {tool_name}")


def _parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Tool arguments must be a JSON object") from exc

    if not isinstance(arguments, dict):
        raise HTTPException(status_code=400, detail="Tool arguments must be a JSON object")

    return arguments


@router.post("/webhook/call-start")
async def call_start(request: Request) -> dict:
    payload = await request.json()
    call_id = payload.get("call_id") or payload.get("id") or "anonymous-call"
    phone_number = payload.get("phone_number") or payload.get("caller_number") or "unknown"

    db = next(get_db())
    try:
        db.add(
            CallLog(
                call_id=call_id,
                phone_number_called=phone_number,
                status="in_progress",
                transcript="",
                collected_data="{}",
                error_message=None,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()

    return {"status": "accepted", "call_id": call_id}


@router.post("/webhook/call-end-report")
async def call_end_report(request: Request) -> dict:
    payload = await request.json()
    call_id = payload.get("call_id") or payload.get("id") or "anonymous-call"
    transcript = payload.get("transcript") or ""
    status = payload.get("status") or "completed"

    db = next(get_db())
    try:
        log = db.execute(select(CallLog).where(CallLog.call_id == call_id)).scalar_one_or_none()
        if log is None:
            log = CallLog(
                call_id=call_id,
                phone_number_called=payload.get("phone_number_called") or "unknown",
                status=status,
                transcript=transcript,
                collected_data="{}",
            )
            db.add(log)
        else:
            log.status = status
            log.transcript = transcript
        db.commit()
    finally:
        db.close()

    return {"status": "saved", "call_id": call_id}


@router.post("/webhook/tool-call")
async def tool_call(request: Request) -> dict:
    payload = await request.json()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    message = payload.get("message")
    if isinstance(message, dict):
        msg_type = message.get("type")

        # 1. Handle tool calls from Vapi
        if msg_type == "tool-calls":
            tool_call_list = message.get("toolCallList")
            if not isinstance(tool_call_list, list) or not tool_call_list:
                raise HTTPException(status_code=400, detail="toolCallList must be a non-empty array")

            parsed_calls = []
            for tool_call in tool_call_list:
                function = tool_call.get("function") if isinstance(tool_call, dict) else None
                if not isinstance(function, dict):
                    raise HTTPException(status_code=400, detail="Each tool call must include a function")

                tool_call_id = tool_call.get("id")
                tool_name = function.get("name")
                if not isinstance(tool_call_id, str) or not tool_call_id:
                    raise HTTPException(status_code=400, detail="Each tool call must include an id")
                if not isinstance(tool_name, str) or not tool_name:
                    raise HTTPException(status_code=400, detail="Each tool call must include a function name")

                parsed_calls.append(
                    (tool_call_id, tool_name, _parse_tool_arguments(function.get("arguments")))
                )

            return {
                "results": [
                    {
                        "name": tool_name,
                        "toolCallId": tool_call_id,
                        "result": json.dumps(_dispatch_tool(tool_name, tool_inputs)),
                    }
                    for tool_call_id, tool_name, tool_inputs in parsed_calls
                ]
            }

        # 2. Handle end-of-call-report (save transcript and status)
        if msg_type == "end-of-call-report":
            call_info = payload.get("call") or message.get("call") or {}
            call_id = call_info.get("id") or payload.get("id") or "anonymous-call"
            transcript = message.get("transcript") or payload.get("transcript") or ""
            status = message.get("endedReason") or "completed"

            db = next(get_db())
            try:
                log = db.execute(select(CallLog).where(CallLog.call_id == call_id)).scalar_one_or_none()
                if log is None:
                    phone_number = call_info.get("customer", {}).get("number") or "unknown"
                    log = CallLog(
                        call_id=call_id,
                        phone_number_called=phone_number,
                        status=status,
                        transcript=transcript,
                        collected_data="{}",
                    )
                    db.add(log)
                else:
                    log.status = status
                    log.transcript = transcript
                db.commit()
            finally:
                db.close()
            return {"status": "saved", "call_id": call_id}

        # 3. Handle telemetry events (status-update, speech-update, conversation-update, etc.)
        return {"status": "received", "type": msg_type}

    # Fallback for manual or legacy tool call payloads
    tool_inputs = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else payload
    tool_name = tool_inputs.get("tool_name") or payload.get("tool_name") or payload.get("name")
    if not isinstance(tool_name, str) or not tool_name:
        return {"status": "ignored"}
    return _dispatch_tool(tool_name, tool_inputs)
