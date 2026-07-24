---
akashic_id: art_20260710_source-confluent-message-delivery-guaran_fbf7b9
akashic_sha: f48e467cfab1
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Confluent, \"Message Delivery Guarantees\" (Kafka design docs)"
gist: "# SOURCE: Confluent, \"Message Delivery Guarantees\" (Kafka design docs) # URL: https://docs.confluent.io/kafka/design/delivery-semantics.html"
tenant: solo
visibility: fleet
seats: []
category: []
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:30:24"
updated: "2026-07-10T23:30:24"
---
<!-- GENERATED PROJECTION of art_20260710_source-confluent-message-delivery-guaran_fbf7b9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Confluent, "Message Delivery Guarantees" (Kafka design docs)

# SOURCE: Confluent, "Message Delivery Guarantees" (Kafka design docs)
# URL: https://docs.confluent.io/kafka/design/delivery-semantics.html
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Semantic Guarantee Definitions

Kafka defines three message delivery semantics:

**At Most Once:** "Messages are delivered once, and if there is a system failure, messages may be lost and are not redelivered."

**At Least Once:** "Messages are delivered one or more times. If there is a system failure, messages are never lost, but they may be delivered more than once."

**Exactly Once:** "Each message is delivered once and only once. Messages are never lost or read twice even if some part of the system fails."

## Producer-Side Mechanisms

**At Most Once:** Asynchronous "fire and forget" transmission or acknowledgment only from the leader broker. Messages may be lost during failures.

**At Least Once:** Producers resend messages if acknowledgment is not received. Since version 0.11.0.0, an idempotent option is available where "resending a message will not result in duplicate entries in the log, and that log order is maintained" through producer IDs and sequence numbers.

**Exactly Once:** Available since version 0.11.0.0 using transactional delivery. Producers request acknowledgment of receipt and successful replication; resends use idempotency. This increases latency but maximizes durability.

## Consumer-Side Offset Management

**At Most Once:** Consumer saves offset position, THEN processes messages. Crash before processing completes means messages are skipped.

**At Least Once:** Consumer processes messages, THEN saves offset position. Crash after processing but before offset commit causes duplicate processing.

**Exactly Once:** For Kafka-to-Kafka scenarios, transactional producers and consumers coordinate via stored offsets. The consumer's position is "stored as a message in a topic, so offset data is written to Kafka in the same transaction as when processed data is written to the output topics." Two isolation levels exist: read_uncommitted (default) and read_committed.

## External System Considerations

For non-Kafka destinations, Kafka cannot coordinate position storage directly. Connectors handle this separately (e.g., HDFS offsets alongside data).

## Default Behavior

"By default Kafka guarantees at-least-once delivery."
