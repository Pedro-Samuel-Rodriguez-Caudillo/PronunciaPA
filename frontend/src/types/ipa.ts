import type { CompareResponse, ErrorReport, FeedbackPayload } from './api';

export type IpaCliKind =
  | 'ipa.list-sounds'
  | 'ipa.explore'
  | 'ipa.practice.set'
  | 'ipa.practice.result';

export interface IpaSound {
  id?: string;
  ipa?: string;
  label?: string;
  aliases?: string[];
  tags?: string[];
}

export interface IpaExample {
  id?: string;
  text?: string;
  ipa?: string;
  position?: string;
  context?: string;
  source?: string;
  validated?: boolean;
}

export interface IpaCliBase {
  schema_version?: string;
  kind: IpaCliKind;
  request?: Record<string, any>;
  warnings?: string[];
  confidence?: string;
  meta?: Record<string, any>;
}

export interface IpaListSoundsResponse extends IpaCliBase {
  kind: 'ipa.list-sounds';
  sounds: IpaSound[];
}

export interface IpaExploreResponse extends IpaCliBase {
  kind: 'ipa.explore';
  sound?: IpaSound;
  examples: IpaExample[];
}

export interface IpaPracticeSetResponse extends IpaCliBase {
  kind: 'ipa.practice.set';
  sound?: IpaSound;
  items: IpaExample[];
}

export interface IpaPracticeResultResponse extends IpaCliBase {
  kind: 'ipa.practice.result';
  sound?: IpaSound;
  item?: IpaExample;
  compare?: CompareResponse;
  report?: ErrorReport;
  feedback?: FeedbackPayload;
}

export type IpaCliPayload =
  | IpaListSoundsResponse
  | IpaExploreResponse
  | IpaPracticeSetResponse
  | IpaPracticeResultResponse;
