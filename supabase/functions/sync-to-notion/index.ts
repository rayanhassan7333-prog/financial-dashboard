import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.8";

const LEDGER_DB_ID = "36e24426-9ef8-8070-bc1c-ea1ecd148662";
const TRANSFER_DB_ID = "36e24426-9ef8-8098-841d-e2bb26b6418e";

// Setup Supabase Client
const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const supabase = createClient(supabaseUrl, supabaseKey);

async function markQueueDone(queueId: number | null) {
  if (!queueId) return;
  const { error } = await supabase
    .from("sync_queue")
    .update({ status: "done", processed_at: new Date().toISOString(), error_msg: null })
    .eq("id", queueId);
  if (error) console.error("Queue done update failed:", error);
}

async function markQueueError(queueId: number | null, message: string) {
  if (!queueId) return;
  const { error } = await supabase
    .from("sync_queue")
    .update({
      status: "error",
      processed_at: new Date().toISOString(),
      error_msg: message.slice(0, 500),
    })
    .eq("id", queueId);
  if (error) console.error("Queue error update failed:", error);
}

function getNotionHeaders(token: string) {
  return {
    "Authorization": `Bearer ${token}`,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
  };
}

async function findExistingNotionPage(token: string, title: string, date: string, amount: number, isTransfer: boolean): Promise<string | null> {
  const dbId = isTransfer ? TRANSFER_DB_ID : LEDGER_DB_ID;
  const titleProp = isTransfer ? "Name" : "Title";
  try {
    const res = await fetch(`https://api.notion.com/v1/databases/${dbId}/query`, {
      method: "POST",
      headers: getNotionHeaders(token),
      body: JSON.stringify({
        filter: {
          and: [
            { property: "Date", date: { equals: date } },
            { property: "Amount", number: { equals: amount } },
          ]
        }
      }),
    });
    if (res.ok) {
      const data = await res.json();
      for (const page of data.results || []) {
        const titleObj = page.properties?.[titleProp]?.title || [];
        const pageTitle = titleObj[0]?.text?.content || "";
        if (pageTitle.trim().toLowerCase() === title.trim().toLowerCase()) {
          return page.id;
        }
      }
    }
  } catch (e) {
    console.warn("Could not check for existing Notion page:", e);
  }
  return null;
}

Deno.serve(async (req) => {
  let queueId: number | null = null;
  try {
    // 1. Authorization check: verify secret token in header to prevent unauthorized access
    const authHeader = req.headers.get("Authorization");
    const webhookSecret = Deno.env.get("WEBHOOK_SECRET");
    if (webhookSecret && authHeader !== `Bearer ${webhookSecret}`) {
      return new Response("Unauthorized", { status: 401 });
    }

    const notionToken = Deno.env.get("NOTION_TOKEN") || req.headers.get("x-notion-token");
    if (!notionToken) {
      console.error("NOTION_TOKEN not provided in headers or environment secrets.");
      return new Response("Config Error: Missing token", { status: 500 });
    }

    const payload = await req.json();
    const { queue_id, type, table, record, old_record } = payload;
    queueId = typeof queue_id === "number" ? queue_id : Number(queue_id) || null;
    
    console.log(`Processing Webhook Event: ${type} on ${table}`);

    if (type === "DELETE") {
      const notionId = old_record?.notion_id;
      if (notionId) {
        console.log(`Archiving Notion page: ${notionId}`);
        const response = await fetch(`https://api.notion.com/v1/pages/${notionId}`, {
          method: "PATCH",
          headers: getNotionHeaders(notionToken),
          body: JSON.stringify({ archived: true }),
        });
        if (!response.ok) {
          throw new Error(`Notion Archive Error: ${response.status} - ${await response.text()}`);
        }
      }
      await markQueueDone(queueId);
      return new Response("OK", { status: 200 });
    }

    // UPDATE or INSERT
    if (!record) {
      return new Response("Bad Request: Missing record", { status: 400 });
    }

    // Loop Prevention Guard:
    // If this is an UPDATE and only the notion_id or updated_at changed, skip sync to avoid loops
    if (type === "UPDATE" && old_record) {
      const crucialChanged = 
        record.date !== old_record.date ||
        record.title !== old_record.title ||
        Math.abs((record.amount || 0) - (old_record.amount || 0)) > 0.001 ||
        record.notes !== old_record.notes ||
        record.type !== old_record.type ||
        record.account_id !== old_record.account_id ||
        record.source_account_id !== old_record.source_account_id ||
        record.dest_account_id !== old_record.dest_account_id ||
        record.category_id !== old_record.category_id ||
        record.status !== old_record.status ||
        JSON.stringify(record.tags) !== JSON.stringify(old_record.tags);

      if (!crucialChanged) {
        console.log("No crucial columns changed (likely notion_id write-back loop). Skipping.");
        await markQueueDone(queueId);
        return new Response("No-op", { status: 200 });
      }
    }

    // Build wallet ID -> Notion ID map from wallet_accounts_tb
    const { data: walletAccounts } = await supabase
      .from("wallet_accounts_tb")
      .select("id, notion_id");

    const walletNotionMap = new Map<string, string>();
    (walletAccounts || []).forEach((w: { id: string; notion_id: string | null }) => {
      if (w.id && w.notion_id) {
        walletNotionMap.set(w.id, w.notion_id);
      }
    });

    const notionHeaders = getNotionHeaders(notionToken);

    if (table === "wallet_transfer_tb") {
      // ----------------------------------------------------
      // TRANSFER SYNC
      // ----------------------------------------------------
      const sourceNotionId = record.source_account_id ? (walletNotionMap.get(record.source_account_id) || record.source_account_id) : null;
      const destNotionId = record.dest_account_id ? (walletNotionMap.get(record.dest_account_id) || record.dest_account_id) : null;

      const notionProps = {
        "Name": { "title": [{ "text": { "content": record.title } }] },
        "Date": { "date": { "start": record.date } },
        "Amount": { "number": record.amount },
        "FROM": { "relation": sourceNotionId ? [{ "id": sourceNotionId }] : [] },
        "TO": { "relation": destNotionId ? [{ "id": destNotionId }] : [] },
      };

      let notionId = record.notion_id;
      if (!notionId) {
        notionId = await findExistingNotionPage(notionToken, record.title, record.date, record.amount, true);
      }

      if (notionId) {
        // PATCH existing transfer page
        console.log(`Updating Notion transfer page: ${notionId}`);
        const patchRes = await fetch(`https://api.notion.com/v1/pages/${notionId}`, {
          method: "PATCH",
          headers: notionHeaders,
          body: JSON.stringify({ properties: notionProps }),
        });
        if (!patchRes.ok) {
          throw new Error(`Notion Transfer Patch Error: ${patchRes.status} - ${await patchRes.text()}`);
        }
        if (!record.notion_id) {
          // Write notion_id back to Supabase
          const { error } = await supabase
            .from("wallet_transfer_tb")
            .update({ notion_id: notionId, updated_at: new Date().toISOString() })
            .eq("id", record.id);
          if (error) console.error("Database Write-back Error:", error);
        }
      } else {
        // POST new transfer page
        console.log("Creating new Notion transfer page…");
        const res = await fetch("https://api.notion.com/v1/pages", {
          method: "POST",
          headers: notionHeaders,
          body: JSON.stringify({
            parent: { database_id: TRANSFER_DB_ID },
            properties: notionProps,
          }),
        });
        if (res.ok) {
          const page = await res.json();
          // Write notion_id back to Supabase
          const { error } = await supabase
            .from("wallet_transfer_tb")
            .update({ notion_id: page.id, updated_at: new Date().toISOString() })
            .eq("id", record.id);
          if (error) console.error("Database Write-back Error:", error);
          console.log(`Successfully created Notion page & wrote back notion_id: ${page.id}`);
        } else {
          throw new Error(`Notion Transfer Create Error: ${res.status} - ${await res.text()}`);
        }
      }
    } else if (table === "transactions_table") {
      // ----------------------------------------------------
      // TRANSACTION SYNC
      // ----------------------------------------------------
      const walletNotionId = record.account_id ? (walletNotionMap.get(record.account_id) || record.account_id) : null;
      const tagsList = [...(record.tags || [])];
      let categoryName: string | null = null;

      if (record.category_id) {
        const { data: category } = await supabase
          .from("parent_category_tb")
          .select("name")
          .eq("id", record.category_id)
          .maybeSingle();
        categoryName = category?.name || null;
      }
      
      // Query lending record if category is Lending
      if (record.category_id === "36e24426-9ef8-8181-8fa3-ccff59500003") {
        const { data: loan } = await supabase
          .from("lending_records_tb")
          .select("borrower")
          .eq("transaction_id", record.id)
          .maybeSingle();
        if (loan?.borrower) {
          tagsList.push(loan.borrower);
        }
      }

      const notionProps: Record<string, any> = {
        "Title": { "title": [{ "text": { "content": record.title } }] },
        "Date": { "date": { "start": record.date } },
        "Amount": { "number": record.amount },
        "Wallet": { "relation": walletNotionId ? [{ "id": walletNotionId }] : [] },
        "Type": { "select": { "name": record.type === "Income" ? "Income" : "Expense" } },
        "Tag": { "multi_select": Array.from(new Set(tagsList)).map(t => ({ "name": t })) },
      };

      if (record.notes !== undefined) {
        notionProps["Notes"] = { "rich_text": [{ "text": { "content": record.notes || "" } }] };
      }
      
      // Status and Maturity Date properties are only available on Subscriptions category
      if (record.category_id === "36e24426-9ef8-81e7-9234-f268a5beaad1") {
        if (record.status) {
          notionProps["status"] = { "status": { "name": record.status } };
        }
        // Fetch end_date from record or subscriptions_list
        let endDate = record.end_date;
        if (!endDate) {
          const { data: sub } = await supabase
            .from("subscriptions_list")
            .select("end_date")
            .eq("transaction_id", record.id)
            .maybeSingle();
          endDate = sub?.end_date;
        }
        if (endDate) {
          notionProps["Maturity Date"] = { "date": { "start": endDate } };
        }
      }

      if (categoryName) {
        notionProps["Category"] = { "select": { "name": categoryName } };
      }

      let notionId = record.notion_id;
      if (!notionId) {
        notionId = await findExistingNotionPage(notionToken, record.title, record.date, record.amount, false);
      }

      if (notionId) {
        // PATCH existing ledger page
        console.log(`Updating Notion ledger page: ${notionId}`);
        const patchRes = await fetch(`https://api.notion.com/v1/pages/${notionId}`, {
          method: "PATCH",
          headers: notionHeaders,
          body: JSON.stringify({ properties: notionProps }),
        });
        if (!patchRes.ok) {
          throw new Error(`Notion Ledger Patch Error: ${patchRes.status} - ${await patchRes.text()}`);
        }
        if (!record.notion_id) {
          // Write notion_id back to Supabase
          const { error } = await supabase
            .from("transactions_table")
            .update({ notion_id: notionId, updated_at: new Date().toISOString() })
            .eq("id", record.id);
          if (error) console.error("Database Write-back Error:", error);
        }
      } else {
        // POST new ledger page
        console.log("Creating new Notion ledger page…");
        const res = await fetch("https://api.notion.com/v1/pages", {
          method: "POST",
          headers: notionHeaders,
          body: JSON.stringify({
            parent: { database_id: LEDGER_DB_ID },
            properties: notionProps,
          }),
        });
        if (res.ok) {
          const page = await res.json();
          // Write notion_id back to Supabase
          const { error } = await supabase
            .from("transactions_table")
            .update({ notion_id: page.id, updated_at: new Date().toISOString() })
            .eq("id", record.id);
          if (error) console.error("Database Write-back Error:", error);
          console.log(`Successfully created Notion page & wrote back notion_id: ${page.id}`);
        } else {
          throw new Error(`Notion Ledger Create Error: ${res.status} - ${await res.text()}`);
        }
      }
    }

    await markQueueDone(queueId);
    return new Response("OK", { status: 200 });
  } catch (err: any) {
    console.error("Function Error:", err);
    await markQueueError(queueId, err?.message || String(err));
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
