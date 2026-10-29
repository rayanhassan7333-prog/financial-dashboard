import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.4";

const NOTION_VERSION = "2026-03-11";
const LEDGER_DATA_SOURCE_ID = Deno.env.get("NOTION_LEDGER_DATA_SOURCE_ID") || "36e24426-9ef8-8083-a8d0-000b7e61fb41";
const TRANSFER_DATA_SOURCE_ID = Deno.env.get("NOTION_TRANSFER_DATA_SOURCE_ID") || "36e24426-9ef8-800f-be2a-000b0e5aadff";
const WALLET_DATA_SOURCE_ID = Deno.env.get("NOTION_WALLET_DATA_SOURCE_ID") || "36e24426-9ef8-80e2-886f-000b593d2fc4";
const ALLOWED_TABLES = new Set(["transactions_table", "wallet_transfer_tb", "wallet_accounts_tb"]);
const ALLOWED_OPERATIONS = new Set(["INSERT", "UPDATE", "DELETE"]);

const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false, autoRefreshToken: false },
});
let cachedNotionToken: string | null = null;

type EntityType = "transfer" | "ledger" | "wallet";

async function getNotionToken(): Promise<string> {
  if (cachedNotionToken) return cachedNotionToken;
  const { data, error } = await supabase
    .from("sys_config_tb")
    .select("value")
    .eq("key", "NOTION_TOKEN")
    .maybeSingle();
  if (error || !data?.value) throw new Error("Missing server configuration");
  cachedNotionToken = String(data.value);
  return cachedNotionToken;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function notionHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
  };
}

function retryDelayMs(response: Response, attempt: number) {
  const retryAfter = response.headers.get("Retry-After");
  if (retryAfter) {
    const seconds = Number(retryAfter);
    if (Number.isFinite(seconds)) return Math.min(seconds * 1000, 30_000);
    const dateMs = Date.parse(retryAfter);
    if (Number.isFinite(dateMs)) return Math.min(Math.max(dateMs - Date.now(), 0), 30_000);
  }
  return Math.min(500 * 2 ** attempt + Math.random() * 250, 5_000);
}

async function notionFetch(token: string, url: string, init: RequestInit, maxAttempts = 4) {
  let lastError: Error | null = null;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12_000);
    try {
      const response = await fetch(url, {
        ...init,
        headers: { ...notionHeaders(token), ...(init.headers || {}) },
        signal: controller.signal,
      });
      if (response.ok || (response.status !== 429 && response.status < 500)) return response;
      lastError = new Error(`Notion transient error (${response.status}): ${await response.text()}`);
      if (attempt < maxAttempts - 1) await new Promise((resolve) => setTimeout(resolve, retryDelayMs(response, attempt)));
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < maxAttempts - 1) await new Promise((resolve) => setTimeout(resolve, retryDelayMs(new Response(null), attempt)));
    } finally {
      clearTimeout(timeout);
    }
  }
  throw lastError || new Error("Notion request failed");
}

async function verifyWebhookSignature(rawBody: string, signature: string | null, secret: string) {
  if (!signature || !/^[a-f0-9]{64}$/i.test(signature)) return false;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const supplied = Uint8Array.from(signature.match(/.{2}/g) || [], (byte) => Number.parseInt(byte, 16));
  return crypto.subtle.verify("HMAC", key, supplied, new TextEncoder().encode(rawBody));
}

async function claimQueueItem(queueId: number) {
  const { data, error } = await supabase.rpc("fn_claim_sync_queue", { p_queue_id: queueId });
  if (error) throw new Error(`Queue claim failed: ${error.message}`);
  return data === true;
}

async function markQueueDoneAtomic(queueId: number | null, table: string, recordId: string, notionId: string | null) {
  if (!queueId) throw new Error("Missing queue id");
  const { error } = await supabase.rpc("fn_sync_complete_callback", {
    p_queue_id: queueId,
    p_table: table,
    p_record_id: recordId,
    p_notion_id: notionId,
  });
  if (error) throw new Error(`Atomic queue completion failed: ${error.message}`);
}

async function markQueueError(queueId: number | null, message: string) {
  if (!queueId) return;
  const { error } = await supabase
    .from("sync_queue")
    .update({ status: "error", processed_at: new Date().toISOString(), error_msg: message.slice(0, 500) })
    .eq("id", queueId);
  if (error) console.error("Queue error update failed:", error);
}

function dataSourceFor(entityType: EntityType) {
  if (entityType === "wallet") return { id: WALLET_DATA_SOURCE_ID, title: "Name" };
  if (entityType === "transfer") return { id: TRANSFER_DATA_SOURCE_ID, title: "Name" };
  return { id: LEDGER_DATA_SOURCE_ID, title: "Title" };
}

async function queryDataSource(token: string, dataSourceId: string, filter: Record<string, unknown>) {
  const response = await notionFetch(token, `https://api.notion.com/v1/data_sources/${dataSourceId}/query`, {
    method: "POST",
    body: JSON.stringify({ filter, page_size: 10 }),
  });
  if (!response.ok) throw new Error(`Notion query error (${response.status}): ${await response.text()}`);
  return response.json();
}

async function findExistingNotionPage(
  token: string,
  recordId: string,
  title: string,
  date: string | undefined,
  amount: number | undefined,
  entityType: EntityType,
) {
  const source = dataSourceFor(entityType);
  const byId = await queryDataSource(token, source.id, {
    property: "Supabase ID",
    rich_text: { equals: recordId },
  });
  if (byId.results?.[0]?.id) return byId.results[0].id as string;

  const fallbackFilter = entityType === "wallet"
    ? { property: source.title, title: { equals: title } }
    : {
      and: [
        { property: "Date", date: { equals: date } },
        { property: "Amount", number: { equals: amount } },
        { property: source.title, title: { equals: title } },
      ],
    };
  const fallback = await queryDataSource(token, source.id, fallbackFilter);
  return fallback.results?.[0]?.id || null;
}

async function upsertNotionPage(
  token: string,
  entityType: EntityType,
  record: Record<string, any>,
  properties: Record<string, unknown>,
  existingNotionId: string | null,
) {
  const source = dataSourceFor(entityType);
  const withStableId = {
    ...properties,
    "Supabase ID": { rich_text: [{ text: { content: record.id } }] },
  };
  const notionId = existingNotionId || await findExistingNotionPage(
    token,
    record.id,
    record.title || record.name,
    record.date,
    record.amount,
    entityType,
  );

  if (notionId) {
    const response = await notionFetch(token, `https://api.notion.com/v1/pages/${notionId}`, {
      method: "PATCH",
      body: JSON.stringify({ properties: withStableId }),
    });
    if (!response.ok) throw new Error(`Notion page update error (${response.status}): ${await response.text()}`);
    return notionId;
  }

  const response = await notionFetch(token, "https://api.notion.com/v1/pages", {
    method: "POST",
    body: JSON.stringify({
      parent: { type: "data_source_id", data_source_id: source.id },
      properties: withStableId,
    }),
  });
  if (!response.ok) throw new Error(`Notion page create error (${response.status}): ${await response.text()}`);
  return (await response.json()).id as string;
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return jsonResponse({ error: "Method not allowed" }, 405);

  let queueId: number | null = null;
  let targetTable = "";
  let recordId = "";
  try {
    const notionToken = await getNotionToken();

    const rawBody = await req.text();
    if (!await verifyWebhookSignature(rawBody, req.headers.get("x-webhook-signature"), notionToken)) {
      return jsonResponse({ error: "Unauthorized" }, 401);
    }

    const payload = JSON.parse(rawBody);
    const { queue_id, type, table, record, old_record, resolved } = payload;
    queueId = typeof queue_id === "number" ? queue_id : Number(queue_id) || null;
    targetTable = table || "";
    recordId = record?.id || old_record?.id || "";
    if (!queueId || !recordId || !ALLOWED_TABLES.has(targetTable) || !ALLOWED_OPERATIONS.has(type)) {
      return jsonResponse({ error: "Invalid webhook payload" }, 400);
    }
    if (!await claimQueueItem(queueId)) return jsonResponse({ ok: true, already_processed: true });

    if (type === "DELETE") {
      const notionId = old_record?.notion_id;
      if (notionId) {
        const response = await notionFetch(notionToken, `https://api.notion.com/v1/pages/${notionId}`, {
          method: "PATCH",
          body: JSON.stringify({ in_trash: true }),
        });
        if (!response.ok && response.status !== 404) {
          throw new Error(`Notion archive error (${response.status}): ${await response.text()}`);
        }
      }
      await markQueueDoneAtomic(queueId, targetTable, recordId, null);
      return jsonResponse({ ok: true });
    }

    if (!record) return jsonResponse({ error: "Missing record" }, 400);

    if (targetTable === "wallet_accounts_tb") {
      const walletProperties: Record<string, unknown> = {
        Name: { title: [{ text: { content: record.name } }] },
      };
      if (record.account_type) {
        walletProperties["Account Type"] = { select: { name: String(record.account_type).toLowerCase() } };
      }
      const notionId = await upsertNotionPage(notionToken, "wallet", record, walletProperties, record.notion_id || null);
      await markQueueDoneAtomic(queueId, targetTable, record.id, notionId);
    } else if (targetTable === "wallet_transfer_tb") {
      let sourceNotionId = resolved?.source_wallet_notion_id;
      let destNotionId = resolved?.dest_wallet_notion_id;
      if (sourceNotionId === undefined && destNotionId === undefined) {
        const { data: wallets, error } = await supabase
          .from("wallet_accounts_tb")
          .select("id, notion_id")
          .in("id", [record.source_account_id, record.dest_account_id].filter(Boolean));
        if (error) throw error;
        const walletMap = new Map((wallets || []).map((wallet: any) => [wallet.id, wallet.notion_id]));
        sourceNotionId = walletMap.get(record.source_account_id) || null;
        destNotionId = walletMap.get(record.dest_account_id) || null;
      }
      const transferProperties: Record<string, unknown> = {
        Name: { title: [{ text: { content: record.title } }] },
        Date: { date: { start: record.date } },
        Amount: { number: record.amount },
        FROM: { relation: sourceNotionId ? [{ id: sourceNotionId }] : [] },
        TO: { relation: destNotionId ? [{ id: destNotionId }] : [] },
      };
      const rawTags = record.tags ?? record.tag;
      const transferTags: string[] = Array.isArray(rawTags)
        ? rawTags
        : typeof rawTags === "string" && rawTags.trim() !== ""
        ? [rawTags]
        : [];
      if (transferTags.length > 0) {
        transferProperties.Tag = { multi_select: transferTags.map((t: string) => ({ name: String(t) })) };
      } else {
        transferProperties.Tag = { multi_select: [] };
      }
      const notionId = await upsertNotionPage(notionToken, "transfer", record, transferProperties, record.notion_id || null);
      await markQueueDoneAtomic(queueId, targetTable, record.id, notionId);
    } else if (targetTable === "transactions_table") {
      let walletNotionId = resolved?.wallet_notion_id;
      let categoryName = resolved?.category_name;
      let borrowerName = resolved?.borrower;
      let endDate = record.end_date || resolved?.end_date;

      if (walletNotionId === undefined && record.account_id) {
        const { data, error } = await supabase.from("wallet_accounts_tb").select("notion_id").eq("id", record.account_id).maybeSingle();
        if (error) throw error;
        walletNotionId = data?.notion_id || null;
      }
      if (categoryName === undefined && record.category_id) {
        const { data, error } = await supabase.from("parent_category_tb").select("name").eq("id", record.category_id).maybeSingle();
        if (error) throw error;
        categoryName = data?.name || null;
      }
      if (categoryName === "Loans & Debt" && !borrowerName) {
        const { data, error } = await supabase.from("lending_records_tb").select("borrower").eq("transaction_id", record.id).maybeSingle();
        if (error) throw error;
        borrowerName = data?.borrower;
      }
      if (categoryName === "Subscription" && !endDate) {
        const { data, error } = await supabase.from("subscriptions_list").select("end_date").eq("transaction_id", record.id).maybeSingle();
        if (error) throw error;
        endDate = data?.end_date;
      }

      const tags = Array.from(new Set([...(record.tags || []), ...(borrowerName ? [borrowerName] : [])]));
      const properties: Record<string, unknown> = {
        Title: { title: [{ text: { content: record.title } }] },
        Date: { date: { start: record.date } },
        Amount: { number: record.amount },
        Wallet: { relation: walletNotionId ? [{ id: walletNotionId }] : [] },
        Type: { select: { name: record.type === "Income" ? "Income" : "Expense" } },
        Tag: { multi_select: tags.map((tag) => ({ name: tag })) },
        Notes: { rich_text: [{ text: { content: record.notes || "" } }] },
      };
      if (record.status) properties.Status = { select: { name: record.status } };
      if (endDate) properties["Maturity Date"] = { date: { start: endDate } };
      if (categoryName) properties.Category = { select: { name: categoryName } };

      const notionId = await upsertNotionPage(notionToken, "ledger", record, properties, record.notion_id || null);
      await markQueueDoneAtomic(queueId, targetTable, record.id, notionId);
    }

    return jsonResponse({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Function error:", message);
    await markQueueError(queueId, message);
    return jsonResponse({ error: "Sync failed", queue_id: queueId }, 500);
  }
});
