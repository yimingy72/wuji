import type { Scenario } from './domain';

export interface GoalTemplate {
  version: 1;
  objective: string;
  criteria: readonly string[];
}

// Prototype content, not a published API/ScenarioProfileVersion.
export const goalTemplates: Record<Scenario, GoalTemplate> = {
  web_single: {
    version: 1,
    objective: '对授权范围内的单个 Web 系统开展系统性的安全评估，识别可达功能、接口和信任边界，核实有依据的安全问题，并交付可追溯的结论及未完成项。',
    criteria: [
      '已识别入口及主要可达功能、接口和边界，明确本次覆盖对象；新发现但未获授权的资产单列。',
      '对适用的关键检查维度记录实际尝试与依据；未测试、前提缺失、环境阻断或预算停止的项目有具体说明。',
      '每项安全结论说明验证条件、方法、证据和影响边界；证据不足或矛盾的结论保留不确定状态。',
      '已汇总发现、覆盖限制和后续建议，区分目标达成与因限制而部分结束。',
    ],
  },
  ctf: {
    version: 1,
    objective: '在题目和比赛允许的范围内分析挑战，获取符合题意的 Flag 或指定解题结果，并保留可以复核的解题过程。',
    criteria: [
      '已取得并核对 Flag 或题目指定结果，记录匹配题意的依据；平台不自动向比赛服务提交答案。',
      '关键推导、实际操作和必要产物可追溯，明确题目环境及适用前提。',
      '未得到有效结果时，记录已尝试方向、阻断和停止原因，不将预算耗尽写成解题成功。',
    ],
  },
  comprehensive: {
    version: 1,
    objective: '围绕已批准的外部和内部资产，按明确阶段目标开展关联安全评估，验证实际可达的风险路径并记录阶段结果。',
    criteria: [
      '每个已批准阶段的测试对象、前提、执行结果与覆盖限制清晰可查。',
      '关键风险路径有实际验证依据；新的资产或操作范围在取得相应授权前保持候选。',
      '阶段目标、未完成工作、环境与身份限制分别说明；发现关联性不能被写成已获得访问或控制能力。',
    ],
  },
  exercise: {
    version: 1,
    objective: '围绕给定单位，在允许的信息源中整理资产及归属线索，经人工确认测试对象后开展已批准阶段的验证，形成可追溯的阶段结果。',
    criteria: [
      '候选资产具有可核对来源和归属线索，明确仍有歧义的对象。',
      '主动测试对象和阶段获得所需授权，候选收集与已执行验证分别记录。',
      '已批准阶段的发现、实际尝试、未测项与阻断有据可查；等待对象授权不是演练目标达成。',
    ],
  },
  code_audit: {
    version: 1,
    objective: '针对明确版本的代码分析可利用的安全问题，定位相关代码和调用关系；在获准且环境可用时完成动态核实，交付证据及修复建议。',
    criteria: [
      '审计对象固定到实际源码版本，覆盖入口、关键数据流与信任边界；不以仓库地址代替源码快照。',
      '每项结论关联具体位置、触发条件与依据；静态推断、动态证实和未验证假设分别标明。',
      '构建/运行失败、依赖缺失或未获动态许可时明确阻断，不伪造动态验证结果。',
      '汇总问题与修复建议、已覆盖内容和剩余限制。',
    ],
  },
};

export function criteriaText(scenario: Scenario) {
  return goalTemplates[scenario].criteria.join('\n');
}
