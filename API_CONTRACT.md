# ICA – API Contract for Backend Team

> **Frontend Branch:** `frontend+UI`
> **Date:** 2026-02-13
> **Status:** Draft — frontend mocks all endpoints via `st.session_state` until backend implements them.

---

## 1. Authentication

### `POST /auth/login`

| Field | Value |
|---|---|
| **Description** | Authenticate a user and return a session/token. |
| **Request Content-Type** | `application/json` |

**Request Payload:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Success Response (200):**
```json
{
  "token": "jwt-or-session-token-string",
  "user": {
    "username": "string",
    "display_name": "string",
    "role": "admin | user",
    "department": "string",
    "title": "CEO | CFO | COO | CTO | CMO | CHRO | VP Sales | VP Engineering | Analyst | Admin"
  }
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

## 2. User Management (Admin)

### `GET /admin/users`

| Field | Value |
|---|---|
| **Description** | Return all registered users. Requires admin token. |
| **Auth Header** | `Authorization: Bearer <token>` |

**Response (200):**
```json
{
  "users": [
    {
      "username": "string",
      "display_name": "string",
      "role": "admin | user",
      "department": "string",
      "title": "string"
    }
  ]
}
```

### `POST /admin/users`

| Field | Value |
|---|---|
| **Description** | Create a new user. Requires admin token. |
| **Auth Header** | `Authorization: Bearer <token>` |

**Request Payload:**
```json
{
  "username": "string",
  "password": "string",
  "display_name": "string",
  "role": "admin | user",
  "department": "string",
  "title": "string"
}
```

**Success Response (201):**
```json
{
  "message": "User created successfully",
  "user": {
    "username": "string",
    "display_name": "string",
    "role": "admin | user",
    "department": "string",
    "title": "string"
  }
}
```

**Error Response (409):**
```json
{
  "detail": "Username already exists"
}
```

### `DELETE /admin/users/{username}`

| Field | Value |
|---|---|
| **Description** | Delete a user by username. Requires admin token. |
| **Auth Header** | `Authorization: Bearer <token>` |

**Success Response (200):**
```json
{
  "message": "User deleted"
}
```

---

## 3. Context Upload

### `POST /context/upload`

| Field | Value |
|---|---|
| **Description** | Upload a PDF or CSV file as additional context for the AI agent. |
| **Content-Type** | `multipart/form-data` |
| **Auth Header** | `Authorization: Bearer <token>` |

**Form Fields:**
| Name | Type | Description |
|---|---|---|
| `file` | `file` | The PDF or CSV file |
| `domain` | `string` | Target domain (sales, operations, hr, accounting, crm) |
| `description` | `string` | Optional description of the file contents |

**Success Response (200):**
```json
{
  "file_id": "uuid-string",
  "filename": "report.pdf",
  "domain": "sales",
  "status": "processed",
  "message": "File uploaded and indexed successfully"
}
```

**Error Response (400):**
```json
{
  "detail": "Unsupported file type. Allowed: pdf, csv"
}
```

---

## 4. Slack Integration

### `POST /integrations/slack/connect`

| Field | Value |
|---|---|
| **Description** | Connect a Slack workspace for insight notifications. |
| **Auth Header** | `Authorization: Bearer <token>` |

**Request Payload:**
```json
{
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#insights",
  "notify_on": ["high_urgency", "all"]
}
```

**Success Response (200):**
```json
{
  "status": "connected",
  "channel": "#insights",
  "message": "Slack integration configured"
}
```

---

## 5. Insights (Enhanced — List Accumulation)

### `POST /insights`  *(existing — enhanced contract)*

| Field | Value |
|---|---|
| **Description** | Fetch new insights. Backend should return **all active insights** (not just one). |

**Request Payload:**
```json
{
  "domain": "sales",
  "role_context": "CEO"
}
```

**Expected Response (200) — MUST be a list:**
```json
[
  {
    "insight_id": "unique-uuid",
    "meta": {
      "urgency_score": 0.85,
      "confidence_score": 0.92,
      "domain": "sales",
      "generated_at": "2026-02-13T10:30:00Z"
    },
    "content": {
      "headline": "string",
      "summary": "string",
      "recommendations": [
        {
          "action": "string",
          "detail": "string",
          "expected_impact": "string"
        }
      ]
    },
    "visuals": {
      "plotly_data": {
        "data": [],
        "layout": {}
      }
    },
    "reasoning_chain": [
      {
        "step": 1,
        "agent": "string",
        "thought": "string"
      }
    ]
  }
]
```

> **Note:** Until the backend returns multiple insights, the frontend deduplicates by `insight_id` and appends new insights to the accumulated list in `st.session_state`.

---

## 6. Chat / Prompt  *(existing — no changes)*

### `POST /prompt`

**Request Payload:**
```json
{
  "domain": "sales",
  "role_context": "CEO",
  "prompt": "What are our top risks this quarter?"
}
```

**Response (200):**
```json
{
  "chat_response": "string"
}
```

---

## 7. Simulation  *(existing — no changes)*

### `POST /simulation`

*(See existing backend implementation — no contract changes needed.)*
