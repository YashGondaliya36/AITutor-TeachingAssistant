/**
 * Shared TypeScript type definitions for the AI Tutor application
 * Replaces 'any' types with proper type definitions
 */

// ============================================================================
// USER & AUTH TYPES
// ============================================================================

export interface User {
    user_id: string;
    email: string;
    name: string;
    age: number;
    current_grade: string;
    user_type: 'student' | 'parent';
    google_id?: string;
    picture?: string;
    created_at?: string;
    last_login?: string;
}

export interface UserProfile extends User {
    // Extended profile fields
    grade_level?: string;
    subjects?: string[];
    learning_goals?: string[];
    interests?: string[];
    preferred_learning_style?: 'visual' | 'auditory' | 'kinesthetic' | 'mixed';
    parent_email?: string;
    timezone?: string;
}

export interface AuthResponse {
    token: string;
    user: User;
    is_new_user: boolean;
}

export interface SetupTokenData {
    google_id: string;
    email: string;
    name: string;
    picture?: string;
}

// ============================================================================
// QUESTION & PERSEUS TYPES
// ============================================================================

export interface PerseusQuestion {
    question: PerseusQuestionContent;
    answerArea: PerseusAnswerArea;
    hints: PerseusHint[];
    itemDataVersion?: Record<string, unknown>;
    dash_metadata?: DashMetadata;
}

export interface PerseusQuestionContent {
    content: string;
    images?: Record<string, PerseusImage>;
    widgets?: Record<string, PerseusWidget>;
}

export interface PerseusAnswerArea {
    calculator?: boolean;
    chi2Table?: boolean;
    periodicTable?: boolean;
    tTable?: boolean;
    zTable?: boolean;
}

export interface PerseusHint {
    content: string;
    images?: Record<string, PerseusImage>;
    widgets?: Record<string, PerseusWidget>;
}

export interface PerseusImage {
    url: string;
    width: number;
    height: number;
}

export interface PerseusWidget {
    type: string;
    options: Record<string, unknown>;
    alignment?: string;
    graded?: boolean;
}

export interface DashMetadata {
    dash_question_id: string;
    skill_ids: string[];
    difficulty: number;
    expected_time_seconds: number;
    slug: string;
    skill_names: string[];
}

// ============================================================================
// DASH SYSTEM TYPES
// ============================================================================

export interface SkillScore {
    name: string;
    memory_strength: number;
    probability: number;
    practice_count: number;
    correct_count: number;
    accuracy: number;
    last_practice_time: number | null;
}

export interface SkillState {
    [skill_id: string]: SkillScore;
}

export interface QuestionAttempt {
    question_id: string;
    skill_ids: string[];
    is_correct: boolean;
    response_time_seconds: number;
    timestamp?: number;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface ApiResponse<T = unknown> {
    data?: T;
    error?: string;
    message?: string;
    status?: number;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    has_more: boolean;
}

// ============================================================================
// MEDIA & STREAMING TYPES
// ============================================================================

export interface MediaCaptureState {
    cameraEnabled: boolean;
    screenEnabled: boolean;
    audioEnabled: boolean;
}

export interface MediaMixerConfig {
    width: number;
    height: number;
    fps: number;
    quality: number;
    cameraEnabled: boolean;
    screenEnabled: boolean;
    cameraVideoRef: React.RefObject<HTMLVideoElement>;
    screenVideoRef: React.RefObject<HTMLVideoElement>;
}

export interface VideoFrame {
    canvas: HTMLCanvasElement;
    timestamp: number;
}

// ============================================================================
// GEMINI LIVE API TYPES
// ============================================================================

export interface LiveAPIConfig {
    model: string;
    systemInstruction?: string;
    generationConfig?: GenerationConfig;
    speechConfig?: SpeechConfig;
    tools?: Tool[];
}

export interface GenerationConfig {
    temperature?: number;
    topP?: number;
    topK?: number;
    maxOutputTokens?: number;
    responseMimeType?: string;
}

export interface SpeechConfig {
    voiceConfig?: VoiceConfig;
}

export interface VoiceConfig {
    prebuiltVoiceConfig?: {
        voiceName: string;
    };
}

export interface Tool {
    functionDeclarations: FunctionDeclaration[];
}

export interface FunctionDeclaration {
    name: string;
    description: string;
    parameters?: {
        type: string;
        properties: Record<string, PropertyDefinition>;
        required?: string[];
    };
}

export interface PropertyDefinition {
    type: string;
    description: string;
    enum?: string[];
}

export interface LiveAPIMessage {
    type: string;
    data?: unknown;
    error?: string;
}

// ============================================================================
// COMPONENT PROPS TYPES
// ============================================================================

export interface BaseComponentProps {
    className?: string;
    style?: React.CSSProperties;
    children?: React.ReactNode;
}

export interface ButtonProps extends BaseComponentProps {
    onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
    disabled?: boolean;
    variant?: 'primary' | 'secondary' | 'outline' | 'destructive' | 'ghost';
    size?: 'sm' | 'md' | 'lg' | 'icon';
    type?: 'button' | 'submit' | 'reset';
}

export interface InputProps extends BaseComponentProps {
    value?: string | number;
    onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
    onBlur?: (event: React.FocusEvent<HTMLInputElement>) => void;
    placeholder?: string;
    type?: string;
    disabled?: boolean;
    required?: boolean;
    min?: number;
    max?: number;
}

// ============================================================================
// CONTEXT TYPES
// ============================================================================

export interface AuthContextValue {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (token: string, user: User) => void;
    logout: () => void;
}

export interface TutorControlContextValue {
    isConnected: boolean;
    isConnecting: boolean;
    connect: () => Promise<void>;
    disconnect: () => void;
    sendMessage: (message: string) => void;
    // Add other tutor control methods
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type AsyncFunction<T = void> = () => Promise<T>;
export type EventHandler<T = Event> = (event: T) => void;

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface AppError {
    code: string;
    message: string;
    details?: unknown;
    timestamp: number;
}

export class APIError extends Error {
    constructor(
        public code: string,
        message: string,
        public statusCode?: number,
        public details?: unknown
    ) {
        super(message);
        this.name = 'APIError';
    }
}

// ============================================================================
// FORM TYPES
// ============================================================================

export interface FormField<T = string> {
    value: T;
    error?: string;
    touched: boolean;
    dirty: boolean;
}

export interface FormState<T extends Record<string, unknown>> {
    values: T;
    errors: Partial<Record<keyof T, string>>;
    touched: Partial<Record<keyof T, boolean>>;
    isSubmitting: boolean;
    isValid: boolean;
}

// ============================================================================
// EXPORT ALL
// ============================================================================

// Export React for UMD global compatibility
import * as React from 'react';
export { React };
