import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const RECEIPT_VERIFIER_URL = Deno.env.get("RECEIPT_VERIFIER_URL") || "http://receipt-verifier:8000"
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")

serve(async (req) => {
  // Handle CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: { "Access-Control-Allow-Origin": "*" } })
  }

  try {
    const { payment_id } = await req.json()

    if (!payment_id) {
      return new Response(
        JSON.stringify({ error: "payment_id is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    }

    // Get payment details from Supabase
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/payments?id=eq.${payment_id}`,
      {
        method: "GET",
        headers: {
          "apikey": SUPABASE_KEY!,
          "Authorization": `Bearer ${SUPABASE_KEY}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to fetch payment: ${response.statusText}`)
    }

    const payments = await response.json()
    if (!payments || payments.length === 0) {
      return new Response(
        JSON.stringify({ error: "Payment not found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      )
    }

    const payment = payments[0]
    const { receipt_url, account_number, amount } = payment

    if (!receipt_url) {
      return new Response(
        JSON.stringify({ error: "receipt_url not found in payment record" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    }

    // Call the receipt verifier service
    const verifierResponse = await fetch(`${RECEIPT_VERIFIER_URL}/verify/storage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_path: receipt_url,
        account_number: account_number,
        amount: parseFloat(amount),
        payment_id: payment_id,
      }),
    })

    if (!verifierResponse.ok) {
      throw new Error(`Verification failed: ${verifierResponse.statusText}`)
    }

    const verificationResult = await verifierResponse.json()

    // Update payment record with verification result
    await fetch(
      `${SUPABASE_URL}/rest/v1/payments?id=eq.${payment_id}`,
      {
        method: "PATCH",
        headers: {
          "apikey": SUPABASE_KEY!,
          "Authorization": `Bearer ${SUPABASE_KEY}`,
          "Content-Type": "application/json",
          "Prefer": "return=minimal",
        },
        body: JSON.stringify({
          status: verificationResult.status,
          failure_reason: verificationResult.reason,
          verified_at: verificationResult.timestamp,
        }),
      }
    )

    return new Response(
      JSON.stringify({
        success: true,
        payment_id: payment_id,
        verification: verificationResult,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    )
  } catch (error) {
    console.error("Error:", error.message)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    )
  }
})
