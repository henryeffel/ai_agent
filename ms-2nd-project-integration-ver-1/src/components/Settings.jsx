import React from "react";
import {
  Box,
  Heading,
  VStack,
  FormControl,
  FormLabel,
  Switch,
  useColorMode,
  Text,
  Divider,
  Flex,
  Icon,
} from "@chakra-ui/react";
import { FiMoon, FiSun, FiMonitor } from "react-icons/fi";

const Settings = () => {
  // Chakra UI에서 제공하는 다크모드 전용 훅
  const { colorMode, toggleColorMode } = useColorMode();

  return (
    <Box
      p={8}
      w="100%"
      h="100vh"
      bg={colorMode === "light" ? "gray.50" : "gray.900"}
    >
      <VStack spacing={8} align="stretch" maxW="600px" m="0 auto">
        {/* 헤더 */}
        <Box>
          <Heading size="lg" mb={2}>
            설정
          </Heading>
          <Text color="gray.500">
            앱의 화면 모드 및 기타 설정을 변경합니다.
          </Text>
        </Box>

        {/* 설정 카드 */}
        <Box
          bg={colorMode === "light" ? "white" : "gray.800"}
          p={6}
          borderRadius="xl"
          boxShadow="sm"
          border="1px solid"
          borderColor={colorMode === "light" ? "gray.200" : "gray.700"}
        >
          <Flex align="center" mb={4}>
            <Icon as={FiMonitor} boxSize={5} mr={2} color="purple.500" />
            <Text fontSize="lg" fontWeight="bold">
              화면 모드
            </Text>
          </Flex>

          <Divider mb={6} />

          <Flex align="center" justify="space-between">
            <VStack align="start" spacing={0}>
              <Flex align="center" mb={1}>
                <Icon as={colorMode === "light" ? FiSun : FiMoon} mr={2} />
                <Text fontWeight="medium" fontSize="md">
                  {colorMode === "light" ? "라이트 모드" : "다크 모드"} 사용 중
                </Text>
              </Flex>
              <Text fontSize="sm" color="gray.500">
                눈의 피로를 줄이려면 다크 모드를 사용해보세요.
              </Text>
            </VStack>

            {/* 다크모드 스위치 */}
            <Switch
              isChecked={colorMode === "dark"}
              onChange={toggleColorMode}
              colorScheme="purple"
              size="lg"
            />
          </Flex>
        </Box>

        {/* (추후 기능 확장을 위한 빈 공간) */}
        <Box
          bg={colorMode === "light" ? "white" : "gray.800"}
          p={6}
          borderRadius="xl"
          boxShadow="sm"
          border="1px solid"
          borderColor={colorMode === "light" ? "gray.200" : "gray.700"}
        >
          <Text fontSize="lg" fontWeight="bold" mb={4}>
            계정 정보
          </Text>
          <Divider mb={4} />
          <Text color="gray.500">추후 업데이트 예정입니다.</Text>
        </Box>
      </VStack>
    </Box>
  );
};

export default Settings;
