import React, { useState } from "react";
import { Alert, AlertIcon, Badge, Box, Button, Code, Heading, HStack, List, ListItem, SimpleGrid, Text, Textarea, VStack, useToast } from "@chakra-ui/react";
import { FiCheck, FiPlay, FiSearch } from "react-icons/fi";
import Card from "../components/Card";
import { apiRequest } from "../lib/api";

const SAMPLE_TRANSCRIPT = "마케팅 캠페인 성과 회의입니다. 지난 캠페인의 전환율을 검토했고 다음 캠페인 예산안을 금요일까지 작성하기로 결정했습니다. 담당자는 캠페인 결과 보고서를 준비하고 다음 주에 후속 회의를 진행합니다.";
const statusColors = { PENDING_APPROVAL: "orange", APPROVED: "blue", SUCCEEDED: "green", PARTIALLY_SUCCEEDED: "yellow", FAILED: "red" };

export default function DemoWorkflow() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState("");
  const toast = useToast();

  const run = async (label, operation) => {
    setLoading(label);
    try {
      const result = await operation();
      setPlan(result);
    } catch (error) {
      toast({ title: `${label} 실패`, description: error.message, status: "error", duration: 6000, isClosable: true });
    } finally {
      setLoading("");
    }
  };

  const createPlan = () => run("Action Plan 생성", () => apiRequest("/api/v1/action-plans/grounded", {
    method: "POST",
    body: JSON.stringify({ meeting_id: `web-${Date.now()}`, transcript, top_k: 3, min_score: 0.1 }),
  }));
  const approvePlan = () => run("사용자 승인", () => apiRequest(`/api/v1/action-plans/${plan.id}/approve`, { method: "POST", body: "{}" }));
  const executePlan = () => run("Mock Microsoft 365 실행", () => apiRequest(`/api/v1/action-plans/${plan.id}/execute`, { method: "POST" }));

  return (
    <VStack align="stretch" spacing={6}>
      <Box>
        <Badge colorScheme="purple" mb={2}>PUBLIC SAFE DEMO</Badge>
        <Heading size="xl">근거 기반 Agent Workflow</Heading>
        <Text mt={2} color="gray.600">회의록을 사내 지식과 연결하고, 사용자 승인 후에만 Microsoft 365 작업을 Mock으로 실행합니다.</Text>
      </Box>
      <Alert status="info" borderRadius="lg"><AlertIcon />공개 데모에서는 실제 메일·일정·할 일을 만들지 않습니다.</Alert>
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
        <Card>
          <Heading size="md" mb={3}>1. 회의록 입력</Heading>
          <Textarea minH="260px" value={transcript} onChange={(event) => setTranscript(event.target.value)} />
          <Button mt={4} colorScheme="purple" leftIcon={<FiSearch />} onClick={createPlan} isLoading={loading === "Action Plan 생성"} isDisabled={transcript.trim().length < 10 || Boolean(loading)}>
            근거 검색 및 Action Plan 생성
          </Button>
        </Card>
        <Card>
          <HStack justify="space-between" mb={4}>
            <Heading size="md">2. 승인 및 실행</Heading>
            {plan && <Badge colorScheme={statusColors[plan.status] || "gray"}>{plan.status}</Badge>}
          </HStack>
          {!plan ? <Text color="gray.500">분석 결과와 실행 계획이 여기에 표시됩니다.</Text> : (
            <VStack align="stretch" spacing={4}>
              <Box><Text fontWeight="bold">사용한 근거</Text><Text fontSize="sm" color="gray.600">{plan.evidence_chunk_ids.join(", ") || "근거 없음"}</Text></Box>
              <Box>
                <Text fontWeight="bold" mb={2}>제안된 작업</Text>
                <List spacing={2}>{plan.actions.map((action) => (
                  <ListItem key={action.action_id} p={3} bg="gray.50" borderRadius="md">
                    <HStack justify="space-between"><Text>{action.tool.toUpperCase()}</Text><Badge>{action.status}</Badge></HStack>
                    <Code mt={2} fontSize="xs" whiteSpace="pre-wrap">{JSON.stringify(action.payload, null, 2)}</Code>
                    {action.external_resource_id && <Text mt={2} fontSize="xs" color="green.600">Mock resource: {action.external_resource_id}</Text>}
                  </ListItem>
                ))}</List>
              </Box>
              <HStack>
                <Button leftIcon={<FiCheck />} colorScheme="blue" onClick={approvePlan} isLoading={loading === "사용자 승인"} isDisabled={plan.status !== "PENDING_APPROVAL" || Boolean(loading)}>승인</Button>
                <Button leftIcon={<FiPlay />} colorScheme="green" onClick={executePlan} isLoading={loading === "Mock Microsoft 365 실행"} isDisabled={plan.status !== "APPROVED" || Boolean(loading)}>Mock 실행</Button>
              </HStack>
            </VStack>
          )}
        </Card>
      </SimpleGrid>
    </VStack>
  );
}
