import React, { useState } from "react";
import { Alert, AlertIcon, Badge, Box, Button, Code, Heading, HStack, List, ListItem, SimpleGrid, Text, Textarea, VStack, useToast } from "@chakra-ui/react";
import { FiCheck, FiPlay, FiSearch } from "react-icons/fi";
import Card from "../components/Card";
import { apiRequest, createGroundedPlanWithRetry } from "../lib/api";

const SAMPLE_TRANSCRIPT = "다음 주 수요일 고객사 부산 방문을 진행하기로 했습니다. 교통편 예약과 출장비 정산 준비는 금요일까지 완료합니다. 예상 출장비가 10만 원 이상이므로 사내 규정에 따른 팀장 승인도 요청하기로 했습니다.";
const statusColors = { PENDING_APPROVAL: "orange", APPROVED: "blue", SUCCEEDED: "green", PARTIALLY_SUCCEEDED: "yellow", FAILED: "red" };

export default function DemoWorkflow() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState("");
  const [retrying, setRetrying] = useState(false);
  const toast = useToast();

  const run = async (label, operation) => {
    setLoading(label);
    try {
      const result = await operation();
      setPlan(result);
    } catch (error) {
      const nextAction = label === "Action Plan 생성"
        ? " 잠시 후 생성 버튼을 다시 눌러 주세요."
        : " 현재 계획 상태를 확인한 뒤 다시 시도해 주세요.";
      toast({ title: `${label} 실패`, description: `${error.message}${nextAction}`, status: "error", duration: 8000, isClosable: true });
    } finally {
      setLoading("");
      setRetrying(false);
    }
  };

  const createPlan = () => run("Action Plan 생성", () => createGroundedPlanWithRetry(
    { meeting_id: `web-${Date.now()}`, transcript, category: "policy", top_k: 1, min_score: 0.04 },
    () => setRetrying(true),
  ));
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
      <Alert status="warning" borderRadius="lg"><AlertIcon />무료 서버를 시작하는 첫 요청은 최대 60초 정도 걸릴 수 있습니다. 일시적인 AI 오류는 계획 생성에 한해 한 번만 자동 재시도합니다.</Alert>
      {retrying && <Alert status="info" borderRadius="lg"><AlertIcon />AI 응답이 일시적으로 불안정해 계획 생성을 한 번 다시 시도하고 있습니다.</Alert>}
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
              <Box>
                <Text fontWeight="bold" mb={2}>사용한 근거</Text>
                {plan.evidence?.length ? (
                  <VStack align="stretch" spacing={2}>
                    {plan.evidence.map((item) => (
                      <Box key={item.chunk_id} p={3} borderWidth="1px" borderRadius="md" bg="purple.50">
                        <HStack justify="space-between" align="start">
                          <Text fontWeight="semibold">{item.title}</Text>
                          <Badge colorScheme="purple">Similarity {item.similarity_score.toFixed(2)}</Badge>
                        </HStack>
                        <Text mt={2} fontSize="sm" noOfLines={3}>{item.excerpt}</Text>
                        <HStack mt={2} spacing={3} color="gray.600" fontSize="xs">
                          <Text>Category: {item.category}</Text>
                          <Text>Source: {item.source || item.document_id}</Text>
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                ) : <Text fontSize="sm" color="gray.600">표시할 근거가 없습니다.</Text>}
              </Box>
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
