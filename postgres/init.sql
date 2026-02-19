-- Telegram channels to track + last seen message id

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TABLE public.telegram_accounts (
    id bigint NOT NULL,
    account_name text NOT NULL,
    user_id bigint,
    first_name text,
    last_name text,
    username text,
    phone_number text,
    session_file text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    last_comment_time timestamp with time zone,
    comments_count integer DEFAULT 0 NOT NULL,
    health_score integer DEFAULT 100 NOT NULL,
    session_status text DEFAULT 'authorized'::text NOT NULL,
    proxy_id integer,
    proxy_type text,
    proxy_host text,
    proxy_port integer,
    proxy_username text,
    proxy_password text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT telegram_accounts_health_score_check CHECK (((health_score >= 0) AND (health_score <= 100)))
);

CREATE SEQUENCE public.telegram_accounts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.telegram_accounts_id_seq OWNED BY public.telegram_accounts.id;

CREATE TABLE public.telegram_channels (
    id bigint NOT NULL,
    identifier text NOT NULL,
    tg_channel_id bigint,
    last_message_id bigint DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE public.telegram_channels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.telegram_channels_id_seq OWNED BY public.telegram_channels.id;

ALTER TABLE ONLY public.telegram_accounts ALTER COLUMN id SET DEFAULT nextval('public.telegram_accounts_id_seq'::regclass);

ALTER TABLE ONLY public.telegram_channels ALTER COLUMN id SET DEFAULT nextval('public.telegram_channels_id_seq'::regclass);

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_account_name_key UNIQUE (account_name);

ALTER TABLE ONLY public.telegram_accounts
    ADD CONSTRAINT telegram_accounts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.telegram_channels
    ADD CONSTRAINT telegram_channels_identifier_key UNIQUE (identifier);

ALTER TABLE ONLY public.telegram_channels
    ADD CONSTRAINT telegram_channels_pkey PRIMARY KEY (id);

CREATE INDEX idx_telegram_accounts_active ON public.telegram_accounts USING btree (is_active, session_status, health_score) WHERE ((is_active = true) AND (session_status = 'authorized'::text) AND (health_score > 70));

CREATE INDEX idx_telegram_accounts_cooldown ON public.telegram_accounts USING btree (last_comment_time) WHERE (is_active = true);

CREATE INDEX idx_telegram_accounts_selection ON public.telegram_accounts USING btree (last_comment_time, comments_count, health_score) WHERE ((is_active = true) AND (health_score > 70));

CREATE INDEX idx_telegram_channels_active ON public.telegram_channels USING btree (is_active, created_at) WHERE (is_active = true);

CREATE TRIGGER update_telegram_channels_updated_at BEFORE UPDATE ON public.telegram_channels FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

