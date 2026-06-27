{{- define "svc.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "svc.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "svc.labels" -}}
app.kubernetes.io/name: {{ include "svc.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "svc.selectorLabels" -}}
app.kubernetes.io/name: {{ include "svc.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Common env block: ConfigMap (non-secret) + optional Secret (envFrom) */}}
{{- define "svc.envFrom" -}}
- configMapRef:
    name: {{ include "svc.fullname" . }}-config
{{- if .Values.secretName }}
- secretRef:
    name: {{ .Values.secretName }}
{{- end }}
{{- end -}}

{{/* DB connection env, sourced from the CloudNativePG-generated `<cluster>-app`
     secret. Only rendered when postgres.enabled; overrides the ConfigMap's
     USE_SQLITE so the same image runs SQLite in dev and Postgres in prod. */}}
{{- define "svc.dbEnv" -}}
- name: USE_SQLITE
  value: "false"
- name: POSTGRES_HOST
  value: {{ include "svc.fullname" . }}-db-rw
- name: POSTGRES_PORT
  value: "5432"
- name: POSTGRES_DB
  valueFrom:
    secretKeyRef:
      name: {{ include "svc.fullname" . }}-db-app
      key: dbname
- name: POSTGRES_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "svc.fullname" . }}-db-app
      key: username
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "svc.fullname" . }}-db-app
      key: password
{{- end -}}
