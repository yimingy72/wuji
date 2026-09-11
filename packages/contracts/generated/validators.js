import * as wujiAjvFormatsModule from 'ajv-formats/dist/formats.js';
const wujiAjvFormats = 'fullFormats' in wujiAjvFormatsModule
  ? wujiAjvFormatsModule
  : wujiAjvFormatsModule.default;
import * as wujiAjvUcs2LengthModule from 'ajv/dist/runtime/ucs2length.js';
const wujiAjvUcs2Length = typeof wujiAjvUcs2LengthModule.default === 'function'
  ? wujiAjvUcs2LengthModule.default
  : wujiAjvUcs2LengthModule.default.default;
"use strict";
export const validateSession = validate21;
const schema32 = {"type":"object","additionalProperties":false,"required":["user_id","display_name","csrf_token","expires_at","permissions_version"],"properties":{"user_id":{"type":"string","format":"uuid"},"display_name":{"type":"string","minLength":1,"maxLength":100},"csrf_token":{"type":"string","minLength":1,"maxLength":256},"expires_at":{"type":"string","format":"date-time"},"permissions_version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"}}};
const schema33 = {"type":"integer","minimum":1,"maximum":9007199254740991};
const formats0 = /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const formats2 = wujiAjvFormats.fullFormats["date-time"];
const func1 = wujiAjvUcs2Length;

function validate21(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate21.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.user_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "user_id"},message:"must have required property '"+"user_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.display_name === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "display_name"},message:"must have required property '"+"display_name"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.csrf_token === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "csrf_token"},message:"must have required property '"+"csrf_token"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.expires_at === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "expires_at"},message:"must have required property '"+"expires_at"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.permissions_version === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "permissions_version"},message:"must have required property '"+"permissions_version"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
for(const key0 in data){
if(!(((((key0 === "user_id") || (key0 === "display_name")) || (key0 === "csrf_token")) || (key0 === "expires_at")) || (key0 === "permissions_version"))){
const err5 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.user_id !== undefined){
let data0 = data.user_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err6 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
else {
const err7 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data.display_name !== undefined){
let data1 = data.display_name;
if(typeof data1 === "string"){
if(func1(data1) > 100){
const err8 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/maxLength",keyword:"maxLength",params:{limit: 100},message:"must NOT have more than 100 characters"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(func1(data1) < 1){
const err9 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
else {
const err10 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.csrf_token !== undefined){
let data2 = data.csrf_token;
if(typeof data2 === "string"){
if(func1(data2) > 256){
const err11 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/maxLength",keyword:"maxLength",params:{limit: 256},message:"must NOT have more than 256 characters"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(func1(data2) < 1){
const err12 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.expires_at !== undefined){
let data3 = data.expires_at;
if(typeof data3 === "string"){
if(!(formats2.validate(data3))){
const err14 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
else {
const err15 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.permissions_version !== undefined){
let data4 = data.permissions_version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err16 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 9007199254740991 || isNaN(data4)){
const err17 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
}
}
else {
const err19 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
validate21.errors = vErrors;
return errors === 0;
}
validate21.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateProject = validate22;
const schema34 = {"type":"object","additionalProperties":false,"required":["id","tenant_id","name","permissions"],"properties":{"id":{"type":"string","format":"uuid"},"tenant_id":{"type":"string","format":"uuid"},"name":{"type":"string","minLength":1,"maxLength":120},"permissions":{"type":"array","maxItems":10,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Permission"}}}};
const schema35 = {"type":"string","enum":["project.read","task.draft.read","task.draft.write","task.preview","task.read","task.create","task.control","artifact.read","artifact.download_sensitive"]};

function validate22(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate22.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.tenant_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.name === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.permissions === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "permissions"},message:"must have required property '"+"permissions"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
for(const key0 in data){
if(!((((key0 === "id") || (key0 === "tenant_id")) || (key0 === "name")) || (key0 === "permissions"))){
const err4 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err5 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
else {
const err6 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err7 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
else {
const err8 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.name !== undefined){
let data2 = data.name;
if(typeof data2 === "string"){
if(func1(data2) > 120){
const err9 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(func1(data2) < 1){
const err10 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
else {
const err11 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.permissions !== undefined){
let data3 = data.permissions;
if(Array.isArray(data3)){
if(data3.length > 10){
const err12 = {instancePath:instancePath+"/permissions",schemaPath:"#/properties/permissions/maxItems",keyword:"maxItems",params:{limit: 10},message:"must NOT have more than 10 items"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(typeof data4 !== "string"){
const err13 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Permission/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(!(((((((((data4 === "project.read") || (data4 === "task.draft.read")) || (data4 === "task.draft.write")) || (data4 === "task.preview")) || (data4 === "task.read")) || (data4 === "task.create")) || (data4 === "task.control")) || (data4 === "artifact.read")) || (data4 === "artifact.download_sensitive"))){
const err14 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Permission/enum",keyword:"enum",params:{allowedValues: schema35.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
}
else {
const err15 = {instancePath:instancePath+"/permissions",schemaPath:"#/properties/permissions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
}
else {
const err16 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
validate22.errors = vErrors;
return errors === 0;
}
validate22.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateProjectPage = validate23;
const schema36 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Project"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

function validate23(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate23.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate22(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate22.errors : vErrors.concat(validate22.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if((typeof data2 !== "string") && (data2 !== null)){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/type",keyword:"type",params:{type: schema36.properties.next_cursor.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate23.errors = vErrors;
return errors === 0;
}
validate23.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateApprovedScope = validate25;
const schema37 = {"type":"object","additionalProperties":false,"required":["binding","label","valid_until","origins","allowed_path_prefixes","excluded_path_prefixes","allowed_methods","limits"],"properties":{"binding":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBinding"},"label":{"type":"string","minLength":1,"maxLength":120},"valid_until":{"type":"string","format":"date-time"},"origins":{"type":"array","maxItems":20,"items":{"type":"string","format":"uri","pattern":"^https?://"}},"allowed_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"excluded_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"allowed_methods":{"type":"array","maxItems":2,"items":{"type":"string","enum":["GET","HEAD"]}},"limits":{"$ref":"urn:wuji:contracts:0.5#/$defs/Limits"}}};
const schema40 = {"type":"object","additionalProperties":false,"required":["max_total_requests","requests_per_second","max_concurrent_requests","request_timeout_seconds","max_response_bytes","max_runtime_seconds"],"properties":{"max_total_requests":{"type":"integer","minimum":1,"maximum":200},"requests_per_second":{"type":"number","exclusiveMinimum":0,"maximum":2},"max_concurrent_requests":{"type":"integer","minimum":1,"maximum":2},"request_timeout_seconds":{"type":"integer","minimum":1,"maximum":10},"max_response_bytes":{"type":"integer","minimum":1,"maximum":1048576},"max_runtime_seconds":{"type":"integer","minimum":1,"maximum":600}}};
const schema38 = {"type":"object","additionalProperties":false,"required":["policy_id","version"],"properties":{"policy_id":{"type":"string","format":"uuid"},"version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"}}};

function validate26(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate26.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.policy_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "policy_id"},message:"must have required property '"+"policy_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.version === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "policy_id") || (key0 === "version"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.policy_id !== undefined){
let data0 = data.policy_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err3 = {instancePath:instancePath+"/policy_id",schemaPath:"#/properties/policy_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
else {
const err4 = {instancePath:instancePath+"/policy_id",schemaPath:"#/properties/policy_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.version !== undefined){
let data1 = data.version;
if(!(((typeof data1 == "number") && (!(data1 % 1) && !isNaN(data1))) && (isFinite(data1)))){
const err5 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if((typeof data1 == "number") && (isFinite(data1))){
if(data1 > 9007199254740991 || isNaN(data1)){
const err6 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1 < 1 || isNaN(data1)){
const err7 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate26.errors = vErrors;
return errors === 0;
}
validate26.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const formats12 = wujiAjvFormats.fullFormats.uri;
const pattern4 = new RegExp("^https?://", "u");

function validate25(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate25.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.binding === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "binding"},message:"must have required property '"+"binding"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.label === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "label"},message:"must have required property '"+"label"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.valid_until === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "valid_until"},message:"must have required property '"+"valid_until"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.origins === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "origins"},message:"must have required property '"+"origins"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.allowed_path_prefixes === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_path_prefixes"},message:"must have required property '"+"allowed_path_prefixes"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.excluded_path_prefixes === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "excluded_path_prefixes"},message:"must have required property '"+"excluded_path_prefixes"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.allowed_methods === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_methods"},message:"must have required property '"+"allowed_methods"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.limits === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "limits"},message:"must have required property '"+"limits"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "binding") || (key0 === "label")) || (key0 === "valid_until")) || (key0 === "origins")) || (key0 === "allowed_path_prefixes")) || (key0 === "excluded_path_prefixes")) || (key0 === "allowed_methods")) || (key0 === "limits"))){
const err8 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.binding !== undefined){
if(!(validate26(data.binding, {instancePath:instancePath+"/binding",parentData:data,parentDataProperty:"binding",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
errors = vErrors.length;
}
}
if(data.label !== undefined){
let data1 = data.label;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err9 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(func1(data1) < 1){
const err10 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
else {
const err11 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.valid_until !== undefined){
let data2 = data.valid_until;
if(typeof data2 === "string"){
if(!(formats2.validate(data2))){
const err12 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.origins !== undefined){
let data3 = data.origins;
if(Array.isArray(data3)){
if(data3.length > 20){
const err14 = {instancePath:instancePath+"/origins",schemaPath:"#/properties/origins/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(typeof data4 === "string"){
if(!pattern4.test(data4)){
const err15 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/pattern",keyword:"pattern",params:{pattern: "^https?://"},message:"must match pattern \""+"^https?://"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(!(formats12(data4))){
const err16 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/format",keyword:"format",params:{format: "uri"},message:"must match format \""+"uri"+"\""};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
else {
const err17 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
}
else {
const err18 = {instancePath:instancePath+"/origins",schemaPath:"#/properties/origins/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.allowed_path_prefixes !== undefined){
let data5 = data.allowed_path_prefixes;
if(Array.isArray(data5)){
if(data5.length > 100){
const err19 = {instancePath:instancePath+"/allowed_path_prefixes",schemaPath:"#/properties/allowed_path_prefixes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
const len1 = data5.length;
for(let i1=0; i1<len1; i1++){
let data6 = data5[i1];
if(typeof data6 === "string"){
if(func1(data6) > 2048){
const err20 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(func1(data6) < 1){
const err21 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
else {
const err22 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
}
else {
const err23 = {instancePath:instancePath+"/allowed_path_prefixes",schemaPath:"#/properties/allowed_path_prefixes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.excluded_path_prefixes !== undefined){
let data7 = data.excluded_path_prefixes;
if(Array.isArray(data7)){
if(data7.length > 100){
const err24 = {instancePath:instancePath+"/excluded_path_prefixes",schemaPath:"#/properties/excluded_path_prefixes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
const len2 = data7.length;
for(let i2=0; i2<len2; i2++){
let data8 = data7[i2];
if(typeof data8 === "string"){
if(func1(data8) > 2048){
const err25 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(func1(data8) < 1){
const err26 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
else {
const err27 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
}
else {
const err28 = {instancePath:instancePath+"/excluded_path_prefixes",schemaPath:"#/properties/excluded_path_prefixes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.allowed_methods !== undefined){
let data9 = data.allowed_methods;
if(Array.isArray(data9)){
if(data9.length > 2){
const err29 = {instancePath:instancePath+"/allowed_methods",schemaPath:"#/properties/allowed_methods/maxItems",keyword:"maxItems",params:{limit: 2},message:"must NOT have more than 2 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len3 = data9.length;
for(let i3=0; i3<len3; i3++){
let data10 = data9[i3];
if(typeof data10 !== "string"){
const err30 = {instancePath:instancePath+"/allowed_methods/" + i3,schemaPath:"#/properties/allowed_methods/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(!((data10 === "GET") || (data10 === "HEAD"))){
const err31 = {instancePath:instancePath+"/allowed_methods/" + i3,schemaPath:"#/properties/allowed_methods/items/enum",keyword:"enum",params:{allowedValues: schema37.properties.allowed_methods.items.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
}
else {
const err32 = {instancePath:instancePath+"/allowed_methods",schemaPath:"#/properties/allowed_methods/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.limits !== undefined){
let data11 = data.limits;
if(data11 && typeof data11 == "object" && !Array.isArray(data11)){
if(data11.max_total_requests === undefined){
const err33 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if(data11.requests_per_second === undefined){
const err34 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(data11.max_concurrent_requests === undefined){
const err35 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data11.request_timeout_seconds === undefined){
const err36 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
if(data11.max_response_bytes === undefined){
const err37 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(data11.max_runtime_seconds === undefined){
const err38 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
for(const key1 in data11){
if(!((((((key1 === "max_total_requests") || (key1 === "requests_per_second")) || (key1 === "max_concurrent_requests")) || (key1 === "request_timeout_seconds")) || (key1 === "max_response_bytes")) || (key1 === "max_runtime_seconds"))){
const err39 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
if(data11.max_total_requests !== undefined){
let data12 = data11.max_total_requests;
if(!(((typeof data12 == "number") && (!(data12 % 1) && !isNaN(data12))) && (isFinite(data12)))){
const err40 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if((typeof data12 == "number") && (isFinite(data12))){
if(data12 > 200 || isNaN(data12)){
const err41 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data12 < 1 || isNaN(data12)){
const err42 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
}
if(data11.requests_per_second !== undefined){
let data13 = data11.requests_per_second;
if((typeof data13 == "number") && (isFinite(data13))){
if(data13 > 2 || isNaN(data13)){
const err43 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(data13 <= 0 || isNaN(data13)){
const err44 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
}
else {
const err45 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
if(data11.max_concurrent_requests !== undefined){
let data14 = data11.max_concurrent_requests;
if(!(((typeof data14 == "number") && (!(data14 % 1) && !isNaN(data14))) && (isFinite(data14)))){
const err46 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
if((typeof data14 == "number") && (isFinite(data14))){
if(data14 > 2 || isNaN(data14)){
const err47 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if(data14 < 1 || isNaN(data14)){
const err48 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
}
if(data11.request_timeout_seconds !== undefined){
let data15 = data11.request_timeout_seconds;
if(!(((typeof data15 == "number") && (!(data15 % 1) && !isNaN(data15))) && (isFinite(data15)))){
const err49 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
if((typeof data15 == "number") && (isFinite(data15))){
if(data15 > 10 || isNaN(data15)){
const err50 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if(data15 < 1 || isNaN(data15)){
const err51 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
}
if(data11.max_response_bytes !== undefined){
let data16 = data11.max_response_bytes;
if(!(((typeof data16 == "number") && (!(data16 % 1) && !isNaN(data16))) && (isFinite(data16)))){
const err52 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
if((typeof data16 == "number") && (isFinite(data16))){
if(data16 > 1048576 || isNaN(data16)){
const err53 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
if(data16 < 1 || isNaN(data16)){
const err54 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
}
if(data11.max_runtime_seconds !== undefined){
let data17 = data11.max_runtime_seconds;
if(!(((typeof data17 == "number") && (!(data17 % 1) && !isNaN(data17))) && (isFinite(data17)))){
const err55 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
if((typeof data17 == "number") && (isFinite(data17))){
if(data17 > 600 || isNaN(data17)){
const err56 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
if(data17 < 1 || isNaN(data17)){
const err57 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
}
}
}
else {
const err58 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
}
}
else {
const err59 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
validate25.errors = vErrors;
return errors === 0;
}
validate25.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateScopePage = validate28;
const schema41 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ApprovedScope"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

function validate28(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate28.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate25(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate25.errors : vErrors.concat(validate25.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if((typeof data2 !== "string") && (data2 !== null)){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/type",keyword:"type",params:{type: schema41.properties.next_cursor.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate28.errors = vErrors;
return errors === 0;
}
validate28.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskPreview = validate30;
const schema42 = {"type":"object","additionalProperties":false,"required":["preview_id","project_id","draft","input_digest","effective_scope","expires_at","can_create","blockers"],"properties":{"preview_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"draft":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskDraft"},"input_digest":{"$ref":"urn:wuji:contracts:0.5#/$defs/Sha256"},"effective_scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ApprovedScope"},"expires_at":{"type":"string","format":"date-time"},"can_create":{"type":"boolean"},"blockers":{"type":"array","maxItems":20,"items":{"type":"object","additionalProperties":false,"required":["code","message"],"properties":{"code":{"type":"string","enum":["MISSING_ADAPTER","MISSING_IDENTITY","SCOPE_DENIED","AUTHORIZATION_EXPIRED","CREATION_UNAVAILABLE"]},"message":{"type":"string","minLength":1,"maxLength":300}}}}},"allOf":[{"if":{"properties":{"can_create":{"const":true}},"type":"object"},"then":{"properties":{"blockers":{"maxItems":0,"type":"array"}},"type":"object"},"else":{"properties":{"blockers":{"minItems":1,"type":"array"}},"type":"object"}}]};
const schema45 = {"type":"string","pattern":"^[a-f0-9]{64}$"};
const schema43 = {"type":"object","additionalProperties":false,"required":["name","scope","target_url","tool","method","limits"],"properties":{"name":{"type":"string","minLength":1,"maxLength":120},"scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBinding"},"target_url":{"type":"string","format":"uri","maxLength":2048,"pattern":"^https?://"},"tool":{"type":"string","const":"http_observe"},"method":{"type":"string","enum":["GET","HEAD"]},"limits":{"$ref":"urn:wuji:contracts:0.5#/$defs/Limits"}}};

function validate31(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate31.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.name === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scope === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scope"},message:"must have required property '"+"scope"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.target_url === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.tool === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tool"},message:"must have required property '"+"tool"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.method === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "method"},message:"must have required property '"+"method"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.limits === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "limits"},message:"must have required property '"+"limits"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
for(const key0 in data){
if(!((((((key0 === "name") || (key0 === "scope")) || (key0 === "target_url")) || (key0 === "tool")) || (key0 === "method")) || (key0 === "limits"))){
const err6 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.name !== undefined){
let data0 = data.name;
if(typeof data0 === "string"){
if(func1(data0) > 120){
const err7 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(func1(data0) < 1){
const err8 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
else {
const err9 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.scope !== undefined){
if(!(validate26(data.scope, {instancePath:instancePath+"/scope",parentData:data,parentDataProperty:"scope",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
errors = vErrors.length;
}
}
if(data.target_url !== undefined){
let data2 = data.target_url;
if(typeof data2 === "string"){
if(func1(data2) > 2048){
const err10 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(!pattern4.test(data2)){
const err11 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/pattern",keyword:"pattern",params:{pattern: "^https?://"},message:"must match pattern \""+"^https?://"+"\""};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(!(formats12(data2))){
const err12 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/format",keyword:"format",params:{format: "uri"},message:"must match format \""+"uri"+"\""};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.tool !== undefined){
let data3 = data.tool;
if(typeof data3 !== "string"){
const err14 = {instancePath:instancePath+"/tool",schemaPath:"#/properties/tool/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if("http_observe" !== data3){
const err15 = {instancePath:instancePath+"/tool",schemaPath:"#/properties/tool/const",keyword:"const",params:{allowedValue: "http_observe"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.method !== undefined){
let data4 = data.method;
if(typeof data4 !== "string"){
const err16 = {instancePath:instancePath+"/method",schemaPath:"#/properties/method/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(!((data4 === "GET") || (data4 === "HEAD"))){
const err17 = {instancePath:instancePath+"/method",schemaPath:"#/properties/method/enum",keyword:"enum",params:{allowedValues: schema43.properties.method.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.limits !== undefined){
let data5 = data.limits;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.max_total_requests === undefined){
const err18 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data5.requests_per_second === undefined){
const err19 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data5.max_concurrent_requests === undefined){
const err20 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data5.request_timeout_seconds === undefined){
const err21 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data5.max_response_bytes === undefined){
const err22 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data5.max_runtime_seconds === undefined){
const err23 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
for(const key1 in data5){
if(!((((((key1 === "max_total_requests") || (key1 === "requests_per_second")) || (key1 === "max_concurrent_requests")) || (key1 === "request_timeout_seconds")) || (key1 === "max_response_bytes")) || (key1 === "max_runtime_seconds"))){
const err24 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data5.max_total_requests !== undefined){
let data6 = data5.max_total_requests;
if(!(((typeof data6 == "number") && (!(data6 % 1) && !isNaN(data6))) && (isFinite(data6)))){
const err25 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if((typeof data6 == "number") && (isFinite(data6))){
if(data6 > 200 || isNaN(data6)){
const err26 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data6 < 1 || isNaN(data6)){
const err27 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
}
if(data5.requests_per_second !== undefined){
let data7 = data5.requests_per_second;
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 > 2 || isNaN(data7)){
const err28 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data7 <= 0 || isNaN(data7)){
const err29 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
else {
const err30 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data5.max_concurrent_requests !== undefined){
let data8 = data5.max_concurrent_requests;
if(!(((typeof data8 == "number") && (!(data8 % 1) && !isNaN(data8))) && (isFinite(data8)))){
const err31 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if((typeof data8 == "number") && (isFinite(data8))){
if(data8 > 2 || isNaN(data8)){
const err32 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
if(data8 < 1 || isNaN(data8)){
const err33 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
}
if(data5.request_timeout_seconds !== undefined){
let data9 = data5.request_timeout_seconds;
if(!(((typeof data9 == "number") && (!(data9 % 1) && !isNaN(data9))) && (isFinite(data9)))){
const err34 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if((typeof data9 == "number") && (isFinite(data9))){
if(data9 > 10 || isNaN(data9)){
const err35 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data9 < 1 || isNaN(data9)){
const err36 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
}
if(data5.max_response_bytes !== undefined){
let data10 = data5.max_response_bytes;
if(!(((typeof data10 == "number") && (!(data10 % 1) && !isNaN(data10))) && (isFinite(data10)))){
const err37 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if((typeof data10 == "number") && (isFinite(data10))){
if(data10 > 1048576 || isNaN(data10)){
const err38 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
if(data10 < 1 || isNaN(data10)){
const err39 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
}
if(data5.max_runtime_seconds !== undefined){
let data11 = data5.max_runtime_seconds;
if(!(((typeof data11 == "number") && (!(data11 % 1) && !isNaN(data11))) && (isFinite(data11)))){
const err40 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if((typeof data11 == "number") && (isFinite(data11))){
if(data11 > 600 || isNaN(data11)){
const err41 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data11 < 1 || isNaN(data11)){
const err42 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
}
}
else {
const err43 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
}
else {
const err44 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
validate31.errors = vErrors;
return errors === 0;
}
validate31.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const pattern6 = new RegExp("^[a-f0-9]{64}$", "u");

function validate30(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate30.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
const _errs2 = errors;
let valid1 = true;
const _errs3 = errors;
if(errors === _errs3){
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.can_create !== undefined){
if(true !== data.can_create){
const err0 = {};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
}
}
else {
const err1 = {};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
}
var _valid0 = _errs3 === errors;
errors = _errs2;
if(vErrors !== null){
if(_errs2){
vErrors.length = _errs2;
}
else {
vErrors = null;
}
}
let ifClause0;
if(_valid0){
const _errs6 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.blockers !== undefined){
let data1 = data.blockers;
if(Array.isArray(data1)){
if(data1.length > 0){
const err2 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/then/properties/blockers/maxItems",keyword:"maxItems",params:{limit: 0},message:"must NOT have more than 0 items"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
else {
const err3 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/then/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
}
else {
const err4 = {instancePath,schemaPath:"#/allOf/0/then/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
var _valid0 = _errs6 === errors;
valid1 = _valid0;
if(valid1){
var props0 = {};
props0.blockers = true;
props0.can_create = true;
}
ifClause0 = "then";
}
else {
const _errs10 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.blockers !== undefined){
let data2 = data.blockers;
if(Array.isArray(data2)){
if(data2.length < 1){
const err5 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/else/properties/blockers/minItems",keyword:"minItems",params:{limit: 1},message:"must NOT have fewer than 1 items"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
else {
const err6 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/else/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
}
else {
const err7 = {instancePath,schemaPath:"#/allOf/0/else/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = _valid0;
if(valid1){
if(props0 !== true){
props0 = props0 || {};
props0.blockers = true;
}
}
ifClause0 = "else";
}
if(!valid1){
const err8 = {instancePath,schemaPath:"#/allOf/0/if",keyword:"if",params:{failingKeyword: ifClause0},message:"must match \""+ifClause0+"\" schema"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.preview_id === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "preview_id"},message:"must have required property '"+"preview_id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.project_id === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.draft === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "draft"},message:"must have required property '"+"draft"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data.input_digest === undefined){
const err12 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "input_digest"},message:"must have required property '"+"input_digest"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data.effective_scope === undefined){
const err13 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "effective_scope"},message:"must have required property '"+"effective_scope"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data.expires_at === undefined){
const err14 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "expires_at"},message:"must have required property '"+"expires_at"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data.can_create === undefined){
const err15 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "can_create"},message:"must have required property '"+"can_create"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(data.blockers === undefined){
const err16 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "blockers"},message:"must have required property '"+"blockers"+"'"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "preview_id") || (key0 === "project_id")) || (key0 === "draft")) || (key0 === "input_digest")) || (key0 === "effective_scope")) || (key0 === "expires_at")) || (key0 === "can_create")) || (key0 === "blockers"))){
const err17 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.preview_id !== undefined){
let data3 = data.preview_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err18 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
else {
const err19 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err20 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
else {
const err21 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.draft !== undefined){
if(!(validate31(data.draft, {instancePath:instancePath+"/draft",parentData:data,parentDataProperty:"draft",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate31.errors : vErrors.concat(validate31.errors);
errors = vErrors.length;
}
}
if(data.input_digest !== undefined){
let data6 = data.input_digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err22 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
else {
const err23 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.effective_scope !== undefined){
if(!(validate25(data.effective_scope, {instancePath:instancePath+"/effective_scope",parentData:data,parentDataProperty:"effective_scope",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate25.errors : vErrors.concat(validate25.errors);
errors = vErrors.length;
}
}
if(data.expires_at !== undefined){
let data8 = data.expires_at;
if(typeof data8 === "string"){
if(!(formats2.validate(data8))){
const err24 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
else {
const err25 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data.can_create !== undefined){
if(typeof data.can_create !== "boolean"){
const err26 = {instancePath:instancePath+"/can_create",schemaPath:"#/properties/can_create/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.blockers !== undefined){
let data10 = data.blockers;
if(Array.isArray(data10)){
if(data10.length > 20){
const err27 = {instancePath:instancePath+"/blockers",schemaPath:"#/properties/blockers/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
const len0 = data10.length;
for(let i0=0; i0<len0; i0++){
let data11 = data10[i0];
if(data11 && typeof data11 == "object" && !Array.isArray(data11)){
if(data11.code === undefined){
const err28 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/required",keyword:"required",params:{missingProperty: "code"},message:"must have required property '"+"code"+"'"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data11.message === undefined){
const err29 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
for(const key1 in data11){
if(!((key1 === "code") || (key1 === "message"))){
const err30 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data11.code !== undefined){
let data12 = data11.code;
if(typeof data12 !== "string"){
const err31 = {instancePath:instancePath+"/blockers/" + i0+"/code",schemaPath:"#/properties/blockers/items/properties/code/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if(!(((((data12 === "MISSING_ADAPTER") || (data12 === "MISSING_IDENTITY")) || (data12 === "SCOPE_DENIED")) || (data12 === "AUTHORIZATION_EXPIRED")) || (data12 === "CREATION_UNAVAILABLE"))){
const err32 = {instancePath:instancePath+"/blockers/" + i0+"/code",schemaPath:"#/properties/blockers/items/properties/code/enum",keyword:"enum",params:{allowedValues: schema42.properties.blockers.items.properties.code.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data11.message !== undefined){
let data13 = data11.message;
if(typeof data13 === "string"){
if(func1(data13) > 300){
const err33 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/maxLength",keyword:"maxLength",params:{limit: 300},message:"must NOT have more than 300 characters"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if(func1(data13) < 1){
const err34 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
else {
const err35 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
}
else {
const err36 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
}
else {
const err37 = {instancePath:instancePath+"/blockers",schemaPath:"#/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
}
else {
const err38 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
validate30.errors = vErrors;
return errors === 0;
}
validate30.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTask = validate35;
const schema46 = {"type":"object","additionalProperties":false,"required":["id","tenant_id","project_id","name","target_url","scope","version","state","cleanup_state","execution","allowed_actions","assessment_outcome","stop_reason","created_at","updated_at"],"properties":{"id":{"type":"string","format":"uuid"},"tenant_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"name":{"type":"string","minLength":1,"maxLength":120},"target_url":{"type":"string","format":"uri","maxLength":2048,"pattern":"^https?://"},"scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBinding"},"version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"},"state":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskState"},"cleanup_state":{"type":"string","enum":["not_required","pending","cleaning","cleaned","cleanup_pending"]},"execution":{"$ref":"urn:wuji:contracts:0.5#/$defs/ExecutionSummary"},"allowed_actions":{"type":"array","maxItems":3,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskAction"}},"assessment_outcome":{"type":"string","enum":["criteria_met","partial","inconclusive","not_assessed"]},"stop_reason":{"type":["string","null"],"enum":[null,"criteria_met","plan_exhausted","budget_exhausted","deadline_exceeded","user_cancelled","runtime_error","authorization_expired"]},"created_at":{"type":"string","format":"date-time"},"updated_at":{"type":"string","format":"date-time"}},"allOf":[{"if":{"properties":{"state":{"enum":["completed","cancelled","failed"]}},"type":"object"},"then":{"properties":{"execution":{"properties":{"active_calls":{"const":0},"unknown_calls":{"const":0},"egress_state":{"enum":["revoked","not_granted"]}},"type":"object"},"allowed_actions":{"maxItems":0,"type":"array"}},"type":"object"}},{"if":{"properties":{"state":{"const":"paused"}},"type":"object"},"then":{"properties":{"execution":{"properties":{"active_calls":{"const":0},"unknown_calls":{"const":0},"egress_state":{"const":"frozen"}},"type":"object"}},"type":"object"}}]};
const schema48 = {"type":"string","enum":["queued","provisioning","running","completing","completed","pausing","paused","cancelling","cancelled","reconciling","failed"]};
const schema49 = {"type":"object","additionalProperties":false,"required":["active_calls","unknown_calls","egress_state"],"properties":{"active_calls":{"type":"integer","minimum":0,"maximum":9007199254740991},"unknown_calls":{"type":"integer","minimum":0,"maximum":9007199254740991},"egress_state":{"type":"string","enum":["pending","active","frozen","revoked","not_granted","unknown"]}}};
const schema50 = {"type":"string","enum":["pause","resume","cancel"]};
const func22 = Object.prototype.hasOwnProperty;

function validate35(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate35.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
const _errs2 = errors;
let valid1 = true;
const _errs3 = errors;
if(errors === _errs3){
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.state !== undefined){
let data0 = data.state;
if(!(((data0 === "completed") || (data0 === "cancelled")) || (data0 === "failed"))){
const err0 = {};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
}
}
else {
const err1 = {};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
}
var _valid0 = _errs3 === errors;
errors = _errs2;
if(vErrors !== null){
if(_errs2){
vErrors.length = _errs2;
}
else {
vErrors = null;
}
}
if(_valid0){
const _errs6 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.execution !== undefined){
let data1 = data.execution;
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.active_calls !== undefined){
if(0 !== data1.active_calls){
const err2 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"#/allOf/0/then/properties/execution/properties/active_calls/const",keyword:"const",params:{allowedValue: 0},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data1.unknown_calls !== undefined){
if(0 !== data1.unknown_calls){
const err3 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"#/allOf/0/then/properties/execution/properties/unknown_calls/const",keyword:"const",params:{allowedValue: 0},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
if(data1.egress_state !== undefined){
let data4 = data1.egress_state;
if(!((data4 === "revoked") || (data4 === "not_granted"))){
const err4 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"#/allOf/0/then/properties/execution/properties/egress_state/enum",keyword:"enum",params:{allowedValues: schema46.allOf[0].then.properties.execution.properties.egress_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
}
else {
const err5 = {instancePath:instancePath+"/execution",schemaPath:"#/allOf/0/then/properties/execution/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.allowed_actions !== undefined){
let data5 = data.allowed_actions;
if(Array.isArray(data5)){
if(data5.length > 0){
const err6 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/allOf/0/then/properties/allowed_actions/maxItems",keyword:"maxItems",params:{limit: 0},message:"must NOT have more than 0 items"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
else {
const err7 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/allOf/0/then/properties/allowed_actions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/allOf/0/then/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
var _valid0 = _errs6 === errors;
valid1 = _valid0;
if(valid1){
var props0 = {};
props0.execution = true;
props0.allowed_actions = true;
props0.state = true;
}
}
if(!valid1){
const err9 = {instancePath,schemaPath:"#/allOf/0/if",keyword:"if",params:{failingKeyword: "then"},message:"must match \"then\" schema"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
const _errs16 = errors;
let valid5 = true;
const _errs17 = errors;
if(errors === _errs17){
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.state !== undefined){
if("paused" !== data.state){
const err10 = {};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
}
else {
const err11 = {};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
var _valid1 = _errs17 === errors;
errors = _errs16;
if(vErrors !== null){
if(_errs16){
vErrors.length = _errs16;
}
else {
vErrors = null;
}
}
if(_valid1){
const _errs20 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.execution !== undefined){
let data7 = data.execution;
if(data7 && typeof data7 == "object" && !Array.isArray(data7)){
if(data7.active_calls !== undefined){
if(0 !== data7.active_calls){
const err12 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"#/allOf/1/then/properties/execution/properties/active_calls/const",keyword:"const",params:{allowedValue: 0},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data7.unknown_calls !== undefined){
if(0 !== data7.unknown_calls){
const err13 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"#/allOf/1/then/properties/execution/properties/unknown_calls/const",keyword:"const",params:{allowedValue: 0},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data7.egress_state !== undefined){
if("frozen" !== data7.egress_state){
const err14 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"#/allOf/1/then/properties/execution/properties/egress_state/const",keyword:"const",params:{allowedValue: "frozen"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
}
else {
const err15 = {instancePath:instancePath+"/execution",schemaPath:"#/allOf/1/then/properties/execution/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
}
else {
const err16 = {instancePath,schemaPath:"#/allOf/1/then/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
var _valid1 = _errs20 === errors;
valid5 = _valid1;
if(valid5){
var props1 = {};
props1.execution = true;
props1.state = true;
}
}
if(!valid5){
const err17 = {instancePath,schemaPath:"#/allOf/1/if",keyword:"if",params:{failingKeyword: "then"},message:"must match \"then\" schema"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(props0 !== true && props1 !== undefined){
if(props1 === true){
props0 = true;
}
else {
props0 = props0 || {};
Object.assign(props0, props1);
}
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.id === undefined){
const err18 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data.tenant_id === undefined){
const err19 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data.project_id === undefined){
const err20 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data.name === undefined){
const err21 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data.target_url === undefined){
const err22 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data.scope === undefined){
const err23 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scope"},message:"must have required property '"+"scope"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
if(data.version === undefined){
const err24 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if(data.state === undefined){
const err25 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(data.cleanup_state === undefined){
const err26 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cleanup_state"},message:"must have required property '"+"cleanup_state"+"'"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data.execution === undefined){
const err27 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "execution"},message:"must have required property '"+"execution"+"'"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
if(data.allowed_actions === undefined){
const err28 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_actions"},message:"must have required property '"+"allowed_actions"+"'"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data.assessment_outcome === undefined){
const err29 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "assessment_outcome"},message:"must have required property '"+"assessment_outcome"+"'"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
if(data.stop_reason === undefined){
const err30 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "stop_reason"},message:"must have required property '"+"stop_reason"+"'"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(data.created_at === undefined){
const err31 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if(data.updated_at === undefined){
const err32 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema46.properties, key0))){
const err33 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
if(data.id !== undefined){
let data11 = data.id;
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err34 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
else {
const err35 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data12 = data.tenant_id;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err36 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
else {
const err37 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
if(data.project_id !== undefined){
let data13 = data.project_id;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err38 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
else {
const err39 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
if(data.name !== undefined){
let data14 = data.name;
if(typeof data14 === "string"){
if(func1(data14) > 120){
const err40 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if(func1(data14) < 1){
const err41 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
if(data.target_url !== undefined){
let data15 = data.target_url;
if(typeof data15 === "string"){
if(func1(data15) > 2048){
const err43 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(!pattern4.test(data15)){
const err44 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/pattern",keyword:"pattern",params:{pattern: "^https?://"},message:"must match pattern \""+"^https?://"+"\""};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
if(!(formats12(data15))){
const err45 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/format",keyword:"format",params:{format: "uri"},message:"must match format \""+"uri"+"\""};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
else {
const err46 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.scope !== undefined){
if(!(validate26(data.scope, {instancePath:instancePath+"/scope",parentData:data,parentDataProperty:"scope",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
errors = vErrors.length;
}
}
if(data.version !== undefined){
let data17 = data.version;
if(!(((typeof data17 == "number") && (!(data17 % 1) && !isNaN(data17))) && (isFinite(data17)))){
const err47 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if((typeof data17 == "number") && (isFinite(data17))){
if(data17 > 9007199254740991 || isNaN(data17)){
const err48 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
if(data17 < 1 || isNaN(data17)){
const err49 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
}
if(data.state !== undefined){
let data18 = data.state;
if(typeof data18 !== "string"){
const err50 = {instancePath:instancePath+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskState/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if(!(((((((((((data18 === "queued") || (data18 === "provisioning")) || (data18 === "running")) || (data18 === "completing")) || (data18 === "completed")) || (data18 === "pausing")) || (data18 === "paused")) || (data18 === "cancelling")) || (data18 === "cancelled")) || (data18 === "reconciling")) || (data18 === "failed"))){
const err51 = {instancePath:instancePath+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskState/enum",keyword:"enum",params:{allowedValues: schema48.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
if(data.cleanup_state !== undefined){
let data19 = data.cleanup_state;
if(typeof data19 !== "string"){
const err52 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
if(!(((((data19 === "not_required") || (data19 === "pending")) || (data19 === "cleaning")) || (data19 === "cleaned")) || (data19 === "cleanup_pending"))){
const err53 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/enum",keyword:"enum",params:{allowedValues: schema46.properties.cleanup_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
if(data.execution !== undefined){
let data20 = data.execution;
if(data20 && typeof data20 == "object" && !Array.isArray(data20)){
if(data20.active_calls === undefined){
const err54 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/required",keyword:"required",params:{missingProperty: "active_calls"},message:"must have required property '"+"active_calls"+"'"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
if(data20.unknown_calls === undefined){
const err55 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/required",keyword:"required",params:{missingProperty: "unknown_calls"},message:"must have required property '"+"unknown_calls"+"'"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
if(data20.egress_state === undefined){
const err56 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/required",keyword:"required",params:{missingProperty: "egress_state"},message:"must have required property '"+"egress_state"+"'"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
for(const key1 in data20){
if(!(((key1 === "active_calls") || (key1 === "unknown_calls")) || (key1 === "egress_state"))){
const err57 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
}
if(data20.active_calls !== undefined){
let data21 = data20.active_calls;
if(!(((typeof data21 == "number") && (!(data21 % 1) && !isNaN(data21))) && (isFinite(data21)))){
const err58 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/active_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
if((typeof data21 == "number") && (isFinite(data21))){
if(data21 > 9007199254740991 || isNaN(data21)){
const err59 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/active_calls/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
if(data21 < 0 || isNaN(data21)){
const err60 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/active_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
}
}
if(data20.unknown_calls !== undefined){
let data22 = data20.unknown_calls;
if(!(((typeof data22 == "number") && (!(data22 % 1) && !isNaN(data22))) && (isFinite(data22)))){
const err61 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/unknown_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
if((typeof data22 == "number") && (isFinite(data22))){
if(data22 > 9007199254740991 || isNaN(data22)){
const err62 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/unknown_calls/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
if(data22 < 0 || isNaN(data22)){
const err63 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/unknown_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
}
}
if(data20.egress_state !== undefined){
let data23 = data20.egress_state;
if(typeof data23 !== "string"){
const err64 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/egress_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
if(!((((((data23 === "pending") || (data23 === "active")) || (data23 === "frozen")) || (data23 === "revoked")) || (data23 === "not_granted")) || (data23 === "unknown"))){
const err65 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/properties/egress_state/enum",keyword:"enum",params:{allowedValues: schema49.properties.egress_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
}
}
else {
const err66 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummary/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
}
if(data.allowed_actions !== undefined){
let data24 = data.allowed_actions;
if(Array.isArray(data24)){
if(data24.length > 3){
const err67 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/maxItems",keyword:"maxItems",params:{limit: 3},message:"must NOT have more than 3 items"};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
const len0 = data24.length;
for(let i0=0; i0<len0; i0++){
let data25 = data24[i0];
if(typeof data25 !== "string"){
const err68 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAction/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
if(!(((data25 === "pause") || (data25 === "resume")) || (data25 === "cancel"))){
const err69 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAction/enum",keyword:"enum",params:{allowedValues: schema50.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
}
}
else {
const err70 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
if(data.assessment_outcome !== undefined){
let data26 = data.assessment_outcome;
if(typeof data26 !== "string"){
const err71 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
if(!((((data26 === "criteria_met") || (data26 === "partial")) || (data26 === "inconclusive")) || (data26 === "not_assessed"))){
const err72 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/enum",keyword:"enum",params:{allowedValues: schema46.properties.assessment_outcome.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err72];
}
else {
vErrors.push(err72);
}
errors++;
}
}
if(data.stop_reason !== undefined){
let data27 = data.stop_reason;
if((typeof data27 !== "string") && (data27 !== null)){
const err73 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/type",keyword:"type",params:{type: schema46.properties.stop_reason.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err73];
}
else {
vErrors.push(err73);
}
errors++;
}
if(!((((((((data27 === null) || (data27 === "criteria_met")) || (data27 === "plan_exhausted")) || (data27 === "budget_exhausted")) || (data27 === "deadline_exceeded")) || (data27 === "user_cancelled")) || (data27 === "runtime_error")) || (data27 === "authorization_expired"))){
const err74 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/enum",keyword:"enum",params:{allowedValues: schema46.properties.stop_reason.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err74];
}
else {
vErrors.push(err74);
}
errors++;
}
}
if(data.created_at !== undefined){
let data28 = data.created_at;
if(typeof data28 === "string"){
if(!(formats2.validate(data28))){
const err75 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err75];
}
else {
vErrors.push(err75);
}
errors++;
}
}
else {
const err76 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err76];
}
else {
vErrors.push(err76);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data29 = data.updated_at;
if(typeof data29 === "string"){
if(!(formats2.validate(data29))){
const err77 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err77];
}
else {
vErrors.push(err77);
}
errors++;
}
}
else {
const err78 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err78];
}
else {
vErrors.push(err78);
}
errors++;
}
}
}
else {
const err79 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err79];
}
else {
vErrors.push(err79);
}
errors++;
}
validate35.errors = vErrors;
return errors === 0;
}
validate35.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskPage = validate37;
const schema51 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Task"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

function validate37(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate37.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate35(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate35.errors : vErrors.concat(validate35.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if((typeof data2 !== "string") && (data2 !== null)){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/type",keyword:"type",params:{type: schema51.properties.next_cursor.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate37.errors = vErrors;
return errors === 0;
}
validate37.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskSnapshot = validate39;
const schema52 = {"type":"object","additionalProperties":false,"required":["task","event_cursor"],"properties":{"task":{"$ref":"urn:wuji:contracts:0.5#/$defs/Task"},"event_cursor":{"$ref":"urn:wuji:contracts:0.5#/$defs/Cursor"}}};
const schema53 = {"type":"string","minLength":1,"maxLength":512};

function validate39(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate39.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.task === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task"},message:"must have required property '"+"task"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.event_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "event_cursor"},message:"must have required property '"+"event_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "task") || (key0 === "event_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.task !== undefined){
if(!(validate35(data.task, {instancePath:instancePath+"/task",parentData:data,parentDataProperty:"task",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate35.errors : vErrors.concat(validate35.errors);
errors = vErrors.length;
}
}
if(data.event_cursor !== undefined){
let data1 = data.event_cursor;
if(typeof data1 === "string"){
if(func1(data1) > 512){
const err3 = {instancePath:instancePath+"/event_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(func1(data1) < 1){
const err4 = {instancePath:instancePath+"/event_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
else {
const err5 = {instancePath:instancePath+"/event_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
}
else {
const err6 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
validate39.errors = vErrors;
return errors === 0;
}
validate39.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateCommandReceipt = validate41;
const schema54 = {"type":"object","additionalProperties":false,"required":["command_id","idempotency_key","kind","disposition","project_id","task_id","accepted_at","accepted_task_version","request_digest"],"properties":{"command_id":{"type":"string","format":"uuid"},"idempotency_key":{"type":"string","format":"uuid"},"kind":{"type":"string","enum":["create","pause","resume","cancel"]},"disposition":{"type":"string","const":"accepted"},"project_id":{"type":"string","format":"uuid"},"task_id":{"type":"string","format":"uuid"},"accepted_at":{"type":"string","format":"date-time"},"accepted_task_version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"},"request_digest":{"$ref":"urn:wuji:contracts:0.5#/$defs/Sha256"}}};

function validate41(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate41.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.command_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "command_id"},message:"must have required property '"+"command_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.idempotency_key === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "idempotency_key"},message:"must have required property '"+"idempotency_key"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.kind === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.disposition === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "disposition"},message:"must have required property '"+"disposition"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.project_id === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.task_id === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task_id"},message:"must have required property '"+"task_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.accepted_at === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "accepted_at"},message:"must have required property '"+"accepted_at"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.accepted_task_version === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "accepted_task_version"},message:"must have required property '"+"accepted_task_version"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.request_digest === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "request_digest"},message:"must have required property '"+"request_digest"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema54.properties, key0))){
const err9 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.command_id !== undefined){
let data0 = data.command_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err10 = {instancePath:instancePath+"/command_id",schemaPath:"#/properties/command_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
else {
const err11 = {instancePath:instancePath+"/command_id",schemaPath:"#/properties/command_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.idempotency_key !== undefined){
let data1 = data.idempotency_key;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err12 = {instancePath:instancePath+"/idempotency_key",schemaPath:"#/properties/idempotency_key/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/idempotency_key",schemaPath:"#/properties/idempotency_key/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.kind !== undefined){
let data2 = data.kind;
if(typeof data2 !== "string"){
const err14 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(!((((data2 === "create") || (data2 === "pause")) || (data2 === "resume")) || (data2 === "cancel"))){
const err15 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/enum",keyword:"enum",params:{allowedValues: schema54.properties.kind.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.disposition !== undefined){
let data3 = data.disposition;
if(typeof data3 !== "string"){
const err16 = {instancePath:instancePath+"/disposition",schemaPath:"#/properties/disposition/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if("accepted" !== data3){
const err17 = {instancePath:instancePath+"/disposition",schemaPath:"#/properties/disposition/const",keyword:"const",params:{allowedValue: "accepted"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err18 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
else {
const err19 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.task_id !== undefined){
let data5 = data.task_id;
if(typeof data5 === "string"){
if(!(formats0.test(data5))){
const err20 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
else {
const err21 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.accepted_at !== undefined){
let data6 = data.accepted_at;
if(typeof data6 === "string"){
if(!(formats2.validate(data6))){
const err22 = {instancePath:instancePath+"/accepted_at",schemaPath:"#/properties/accepted_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
else {
const err23 = {instancePath:instancePath+"/accepted_at",schemaPath:"#/properties/accepted_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.accepted_task_version !== undefined){
let data7 = data.accepted_task_version;
if(!(((typeof data7 == "number") && (!(data7 % 1) && !isNaN(data7))) && (isFinite(data7)))){
const err24 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 > 9007199254740991 || isNaN(data7)){
const err25 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(data7 < 1 || isNaN(data7)){
const err26 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
}
if(data.request_digest !== undefined){
let data8 = data.request_digest;
if(typeof data8 === "string"){
if(!pattern6.test(data8)){
const err27 = {instancePath:instancePath+"/request_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/request_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
}
else {
const err29 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
validate41.errors = vErrors;
return errors === 0;
}
validate41.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateEventPage = validate42;
const schema57 = {"type":"object","additionalProperties":false,"required":["items","next_cursor","has_more"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskEvent"}},"next_cursor":{"$ref":"urn:wuji:contracts:0.5#/$defs/Cursor"},"has_more":{"type":"boolean"}}};
const schema58 = {"type":"object","additionalProperties":false,"required":["schema_version","event_id","cursor","tenant_id","project_id","task_id","aggregate_version","type","occurred_at","trace_id","summary"],"properties":{"schema_version":{"type":"string","const":"1.0"},"event_id":{"type":"string","format":"uuid"},"cursor":{"$ref":"urn:wuji:contracts:0.5#/$defs/Cursor"},"tenant_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"task_id":{"type":"string","format":"uuid"},"aggregate_version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"},"type":{"type":"string","enum":["task.changed","task.cleanup_changed","artifact.available"]},"occurred_at":{"type":"string","format":"date-time"},"trace_id":{"type":"string","format":"uuid"},"summary":{"type":"string","minLength":1,"maxLength":500}}};

function validate43(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate43.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.event_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "event_id"},message:"must have required property '"+"event_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.cursor === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cursor"},message:"must have required property '"+"cursor"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.tenant_id === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.project_id === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.task_id === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task_id"},message:"must have required property '"+"task_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.aggregate_version === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "aggregate_version"},message:"must have required property '"+"aggregate_version"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.type === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "type"},message:"must have required property '"+"type"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.occurred_at === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "occurred_at"},message:"must have required property '"+"occurred_at"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.trace_id === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "trace_id"},message:"must have required property '"+"trace_id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.summary === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "summary"},message:"must have required property '"+"summary"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema58.properties, key0))){
const err11 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err12 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if("1.0" !== data0){
const err13 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.event_id !== undefined){
let data1 = data.event_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err14 = {instancePath:instancePath+"/event_id",schemaPath:"#/properties/event_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
else {
const err15 = {instancePath:instancePath+"/event_id",schemaPath:"#/properties/event_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.cursor !== undefined){
let data2 = data.cursor;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err16 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(func1(data2) < 1){
const err17 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
else {
const err18 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data3 = data.tenant_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err19 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
else {
const err20 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err21 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
else {
const err22 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data.task_id !== undefined){
let data5 = data.task_id;
if(typeof data5 === "string"){
if(!(formats0.test(data5))){
const err23 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
else {
const err24 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data.aggregate_version !== undefined){
let data6 = data.aggregate_version;
if(!(((typeof data6 == "number") && (!(data6 % 1) && !isNaN(data6))) && (isFinite(data6)))){
const err25 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if((typeof data6 == "number") && (isFinite(data6))){
if(data6 > 9007199254740991 || isNaN(data6)){
const err26 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data6 < 1 || isNaN(data6)){
const err27 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
}
if(data.type !== undefined){
let data7 = data.type;
if(typeof data7 !== "string"){
const err28 = {instancePath:instancePath+"/type",schemaPath:"#/properties/type/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(!(((data7 === "task.changed") || (data7 === "task.cleanup_changed")) || (data7 === "artifact.available"))){
const err29 = {instancePath:instancePath+"/type",schemaPath:"#/properties/type/enum",keyword:"enum",params:{allowedValues: schema58.properties.type.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data.occurred_at !== undefined){
let data8 = data.occurred_at;
if(typeof data8 === "string"){
if(!(formats2.validate(data8))){
const err30 = {instancePath:instancePath+"/occurred_at",schemaPath:"#/properties/occurred_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/occurred_at",schemaPath:"#/properties/occurred_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data.trace_id !== undefined){
let data9 = data.trace_id;
if(typeof data9 === "string"){
if(!(formats0.test(data9))){
const err32 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
else {
const err33 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
if(data.summary !== undefined){
let data10 = data.summary;
if(typeof data10 === "string"){
if(func1(data10) > 500){
const err34 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/maxLength",keyword:"maxLength",params:{limit: 500},message:"must NOT have more than 500 characters"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(func1(data10) < 1){
const err35 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
else {
const err36 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
}
else {
const err37 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
validate43.errors = vErrors;
return errors === 0;
}
validate43.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate42(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate42.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.has_more === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "has_more"},message:"must have required property '"+"has_more"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
for(const key0 in data){
if(!(((key0 === "items") || (key0 === "next_cursor")) || (key0 === "has_more"))){
const err3 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate43(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate43.errors : vErrors.concat(validate43.errors);
errors = vErrors.length;
}
}
}
else {
const err5 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
else {
const err8 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.has_more !== undefined){
if(typeof data.has_more !== "boolean"){
const err9 = {instancePath:instancePath+"/has_more",schemaPath:"#/properties/has_more/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
}
else {
const err10 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
validate42.errors = vErrors;
return errors === 0;
}
validate42.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateSavedTaskDraft = validate45;
const schema62 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"tenant_id":{"format":"uuid","title":"Tenant Id","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"user_id":{"format":"uuid","title":"User Id","type":"string"},"version":{"maximum":9007199254740991,"minimum":1,"title":"Version","type":"integer"},"content":{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft"}],"title":"Content"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","tenant_id","project_id","user_id","version","content","created_at","updated_at"],"title":"TaskDraftResponse","type":"object"};
const schema63 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"ctf","title":"Scenario","type":"string"},"challenge":{"default":"","maxLength":8000,"title":"Challenge","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"}},"required":["scenario"],"title":"CtfDraft","type":"object"};
const schema64 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"web_single","title":"Scenario","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"},"include_subdomains":{"default":false,"title":"Include Subdomains","type":"boolean"},"additional_origins":{"items":{"maxLength":2048,"type":"string"},"maxItems":100,"title":"Additional Origins","type":"array"}},"required":["scenario"],"title":"WebDraft","type":"object"};
const schema65 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"comprehensive","title":"Scenario","type":"string"},"assets":{"items":{"maxLength":2048,"type":"string"},"maxItems":100,"title":"Assets","type":"array"},"access_notes":{"default":"","maxLength":4000,"title":"Access Notes","type":"string"}},"required":["scenario"],"title":"ComprehensiveDraft","type":"object"};
const schema66 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"exercise","title":"Scenario","type":"string"},"organization_name":{"default":"","maxLength":255,"title":"Organization Name","type":"string"},"known_domains":{"items":{"maxLength":253,"type":"string"},"maxItems":100,"title":"Known Domains","type":"array"}},"required":["scenario"],"title":"ExerciseDraft","type":"object"};
const schema67 = {"additionalProperties":false,"not":{"properties":{"repository_url":{"type":"string"},"source_reference_id":{"type":"string"}},"required":["repository_url","source_reference_id"]},"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"code_audit","title":"Scenario","type":"string"},"repository_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Repository Url"},"source_reference_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Source Reference Id"},"revision":{"anyOf":[{"maxLength":255,"type":"string"},{"type":"null"}],"default":null,"title":"Revision"}},"required":["scenario"],"title":"CodeAuditDraft","type":"object"};
const pattern9 = new RegExp("^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$", "u");

function validate45(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate45.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.tenant_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.project_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.user_id === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "user_id"},message:"must have required property '"+"user_id"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.version === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.content === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "content"},message:"must have required property '"+"content"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.created_at === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.updated_at === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "id") || (key0 === "tenant_id")) || (key0 === "project_id")) || (key0 === "user_id")) || (key0 === "version")) || (key0 === "content")) || (key0 === "created_at")) || (key0 === "updated_at"))){
const err8 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err9 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
else {
const err10 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err11 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
else {
const err12 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.project_id !== undefined){
let data2 = data.project_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err13 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
else {
const err14 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data.user_id !== undefined){
let data3 = data.user_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err15 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
else {
const err16 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.version !== undefined){
let data4 = data.version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err17 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 9007199254740991 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err19 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
if(data.content !== undefined){
let data5 = data.content;
const _errs13 = errors;
let valid1 = false;
let passing0 = null;
const _errs14 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err20 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
for(const key1 in data5){
if(!(func22.call(schema63.properties, key1))){
const err21 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data6 = data5.schema_version;
if(typeof data6 !== "string"){
const err22 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if("1.0" !== data6){
const err23 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data5.name !== undefined){
let data7 = data5.name;
if(typeof data7 === "string"){
if(func1(data7) > 120){
const err24 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
else {
const err25 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data5.objective !== undefined){
let data8 = data5.objective;
if(typeof data8 === "string"){
if(func1(data8) > 8000){
const err26 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
else {
const err27 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data9 = data5.starting_point;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err28 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data10 = data5.constraints;
if(typeof data10 === "string"){
if(func1(data10) > 4000){
const err30 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data11 = data5.reference_ids;
if(Array.isArray(data11)){
if(data11.length > 20){
const err32 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
const len0 = data11.length;
for(let i0=0; i0<len0; i0++){
let data12 = data11[i0];
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
}
else {
const err35 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data13 = data5.model_profile_version_id;
const _errs33 = errors;
let valid6 = false;
const _errs34 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err36 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
else {
const err37 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid6 = valid6 || _valid1;
const _errs36 = errors;
if(data13 !== null){
const err38 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid6 = valid6 || _valid1;
if(!valid6){
const err39 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data14 = data5.runtime_profile_version_id;
const _errs39 = errors;
let valid7 = false;
const _errs40 = errors;
if(typeof data14 === "string"){
if(!(formats0.test(data14))){
const err40 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
else {
const err41 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid7 = valid7 || _valid2;
const _errs42 = errors;
if(data14 !== null){
const err42 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid7 = valid7 || _valid2;
if(!valid7){
const err43 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data15 = data5.budget_usd;
const _errs45 = errors;
const _errs46 = errors;
if(!(((((((data15 === "0") || (data15 === "0.0")) || (data15 === "0.00")) || (data15 === "0.000")) || (data15 === "0.0000")) || (data15 === "0.00000")) || (data15 === "0.000000"))){
const err44 = {};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
var valid8 = _errs46 === errors;
if(valid8){
const err45 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
const _errs47 = errors;
let valid9 = false;
const _errs48 = errors;
if(typeof data15 === "string"){
if(!pattern9.test(data15)){
const err46 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
else {
const err47 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid9 = valid9 || _valid3;
const _errs50 = errors;
if(data15 !== null){
const err48 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
var _valid3 = _errs50 === errors;
valid9 = valid9 || _valid3;
if(!valid9){
const err49 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
else {
errors = _errs47;
if(vErrors !== null){
if(_errs47){
vErrors.length = _errs47;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data16 = data5.scenario;
if(typeof data16 !== "string"){
const err50 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if("ctf" !== data16){
const err51 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "ctf"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
if(data5.challenge !== undefined){
let data17 = data5.challenge;
if(typeof data17 === "string"){
if(func1(data17) > 8000){
const err52 = {instancePath:instancePath+"/content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
else {
const err53 = {instancePath:instancePath+"/content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data18 = data5.entry_url;
const _errs57 = errors;
let valid10 = false;
const _errs58 = errors;
if(typeof data18 === "string"){
if(func1(data18) > 2048){
const err54 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
else {
const err55 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
var _valid4 = _errs58 === errors;
valid10 = valid10 || _valid4;
const _errs60 = errors;
if(data18 !== null){
const err56 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
var _valid4 = _errs60 === errors;
valid10 = valid10 || _valid4;
if(!valid10){
const err57 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
else {
errors = _errs57;
if(vErrors !== null){
if(_errs57){
vErrors.length = _errs57;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err58 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
var _valid0 = _errs14 === errors;
if(_valid0){
valid1 = true;
passing0 = 0;
var props0 = true;
}
const _errs62 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err59 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
for(const key2 in data5){
if(!(func22.call(schema64.properties, key2))){
const err60 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data19 = data5.schema_version;
if(typeof data19 !== "string"){
const err61 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
if("1.0" !== data19){
const err62 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
if(data5.name !== undefined){
let data20 = data5.name;
if(typeof data20 === "string"){
if(func1(data20) > 120){
const err63 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
}
else {
const err64 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
}
if(data5.objective !== undefined){
let data21 = data5.objective;
if(typeof data21 === "string"){
if(func1(data21) > 8000){
const err65 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
}
else {
const err66 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data22 = data5.starting_point;
if(typeof data22 === "string"){
if(func1(data22) > 8000){
const err67 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
}
else {
const err68 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data23 = data5.constraints;
if(typeof data23 === "string"){
if(func1(data23) > 4000){
const err69 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
}
else {
const err70 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data24 = data5.reference_ids;
if(Array.isArray(data24)){
if(data24.length > 20){
const err71 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
const len1 = data24.length;
for(let i1=0; i1<len1; i1++){
let data25 = data24[i1];
if(typeof data25 === "string"){
if(!(formats0.test(data25))){
const err72 = {instancePath:instancePath+"/content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err72];
}
else {
vErrors.push(err72);
}
errors++;
}
}
else {
const err73 = {instancePath:instancePath+"/content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err73];
}
else {
vErrors.push(err73);
}
errors++;
}
}
}
else {
const err74 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err74];
}
else {
vErrors.push(err74);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data26 = data5.model_profile_version_id;
const _errs81 = errors;
let valid15 = false;
const _errs82 = errors;
if(typeof data26 === "string"){
if(!(formats0.test(data26))){
const err75 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err75];
}
else {
vErrors.push(err75);
}
errors++;
}
}
else {
const err76 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err76];
}
else {
vErrors.push(err76);
}
errors++;
}
var _valid5 = _errs82 === errors;
valid15 = valid15 || _valid5;
const _errs84 = errors;
if(data26 !== null){
const err77 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err77];
}
else {
vErrors.push(err77);
}
errors++;
}
var _valid5 = _errs84 === errors;
valid15 = valid15 || _valid5;
if(!valid15){
const err78 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err78];
}
else {
vErrors.push(err78);
}
errors++;
}
else {
errors = _errs81;
if(vErrors !== null){
if(_errs81){
vErrors.length = _errs81;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data27 = data5.runtime_profile_version_id;
const _errs87 = errors;
let valid16 = false;
const _errs88 = errors;
if(typeof data27 === "string"){
if(!(formats0.test(data27))){
const err79 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err79];
}
else {
vErrors.push(err79);
}
errors++;
}
}
else {
const err80 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err80];
}
else {
vErrors.push(err80);
}
errors++;
}
var _valid6 = _errs88 === errors;
valid16 = valid16 || _valid6;
const _errs90 = errors;
if(data27 !== null){
const err81 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err81];
}
else {
vErrors.push(err81);
}
errors++;
}
var _valid6 = _errs90 === errors;
valid16 = valid16 || _valid6;
if(!valid16){
const err82 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err82];
}
else {
vErrors.push(err82);
}
errors++;
}
else {
errors = _errs87;
if(vErrors !== null){
if(_errs87){
vErrors.length = _errs87;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data28 = data5.budget_usd;
const _errs93 = errors;
const _errs94 = errors;
if(!(((((((data28 === "0") || (data28 === "0.0")) || (data28 === "0.00")) || (data28 === "0.000")) || (data28 === "0.0000")) || (data28 === "0.00000")) || (data28 === "0.000000"))){
const err83 = {};
if(vErrors === null){
vErrors = [err83];
}
else {
vErrors.push(err83);
}
errors++;
}
var valid17 = _errs94 === errors;
if(valid17){
const err84 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err84];
}
else {
vErrors.push(err84);
}
errors++;
}
else {
errors = _errs93;
if(vErrors !== null){
if(_errs93){
vErrors.length = _errs93;
}
else {
vErrors = null;
}
}
}
const _errs95 = errors;
let valid18 = false;
const _errs96 = errors;
if(typeof data28 === "string"){
if(!pattern9.test(data28)){
const err85 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err85];
}
else {
vErrors.push(err85);
}
errors++;
}
}
else {
const err86 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err86];
}
else {
vErrors.push(err86);
}
errors++;
}
var _valid7 = _errs96 === errors;
valid18 = valid18 || _valid7;
const _errs98 = errors;
if(data28 !== null){
const err87 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err87];
}
else {
vErrors.push(err87);
}
errors++;
}
var _valid7 = _errs98 === errors;
valid18 = valid18 || _valid7;
if(!valid18){
const err88 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err88];
}
else {
vErrors.push(err88);
}
errors++;
}
else {
errors = _errs95;
if(vErrors !== null){
if(_errs95){
vErrors.length = _errs95;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data29 = data5.scenario;
if(typeof data29 !== "string"){
const err89 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err89];
}
else {
vErrors.push(err89);
}
errors++;
}
if("web_single" !== data29){
const err90 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "web_single"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err90];
}
else {
vErrors.push(err90);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data30 = data5.entry_url;
const _errs103 = errors;
let valid19 = false;
const _errs104 = errors;
if(typeof data30 === "string"){
if(func1(data30) > 2048){
const err91 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err91];
}
else {
vErrors.push(err91);
}
errors++;
}
}
else {
const err92 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err92];
}
else {
vErrors.push(err92);
}
errors++;
}
var _valid8 = _errs104 === errors;
valid19 = valid19 || _valid8;
const _errs106 = errors;
if(data30 !== null){
const err93 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err93];
}
else {
vErrors.push(err93);
}
errors++;
}
var _valid8 = _errs106 === errors;
valid19 = valid19 || _valid8;
if(!valid19){
const err94 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err94];
}
else {
vErrors.push(err94);
}
errors++;
}
else {
errors = _errs103;
if(vErrors !== null){
if(_errs103){
vErrors.length = _errs103;
}
else {
vErrors = null;
}
}
}
}
if(data5.include_subdomains !== undefined){
if(typeof data5.include_subdomains !== "boolean"){
const err95 = {instancePath:instancePath+"/content/include_subdomains",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/include_subdomains/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err95];
}
else {
vErrors.push(err95);
}
errors++;
}
}
if(data5.additional_origins !== undefined){
let data32 = data5.additional_origins;
if(Array.isArray(data32)){
if(data32.length > 100){
const err96 = {instancePath:instancePath+"/content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err96];
}
else {
vErrors.push(err96);
}
errors++;
}
const len2 = data32.length;
for(let i2=0; i2<len2; i2++){
let data33 = data32[i2];
if(typeof data33 === "string"){
if(func1(data33) > 2048){
const err97 = {instancePath:instancePath+"/content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err97];
}
else {
vErrors.push(err97);
}
errors++;
}
}
else {
const err98 = {instancePath:instancePath+"/content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err98];
}
else {
vErrors.push(err98);
}
errors++;
}
}
}
else {
const err99 = {instancePath:instancePath+"/content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err99];
}
else {
vErrors.push(err99);
}
errors++;
}
}
}
else {
const err100 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err100];
}
else {
vErrors.push(err100);
}
errors++;
}
var _valid0 = _errs62 === errors;
if(_valid0 && valid1){
valid1 = false;
passing0 = [passing0, 1];
}
else {
if(_valid0){
valid1 = true;
passing0 = 1;
if(props0 !== true){
props0 = true;
}
}
const _errs114 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err101 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err101];
}
else {
vErrors.push(err101);
}
errors++;
}
for(const key3 in data5){
if(!(func22.call(schema65.properties, key3))){
const err102 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key3},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err102];
}
else {
vErrors.push(err102);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data34 = data5.schema_version;
if(typeof data34 !== "string"){
const err103 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err103];
}
else {
vErrors.push(err103);
}
errors++;
}
if("1.0" !== data34){
const err104 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err104];
}
else {
vErrors.push(err104);
}
errors++;
}
}
if(data5.name !== undefined){
let data35 = data5.name;
if(typeof data35 === "string"){
if(func1(data35) > 120){
const err105 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err105];
}
else {
vErrors.push(err105);
}
errors++;
}
}
else {
const err106 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err106];
}
else {
vErrors.push(err106);
}
errors++;
}
}
if(data5.objective !== undefined){
let data36 = data5.objective;
if(typeof data36 === "string"){
if(func1(data36) > 8000){
const err107 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err107];
}
else {
vErrors.push(err107);
}
errors++;
}
}
else {
const err108 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err108];
}
else {
vErrors.push(err108);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data37 = data5.starting_point;
if(typeof data37 === "string"){
if(func1(data37) > 8000){
const err109 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err109];
}
else {
vErrors.push(err109);
}
errors++;
}
}
else {
const err110 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err110];
}
else {
vErrors.push(err110);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data38 = data5.constraints;
if(typeof data38 === "string"){
if(func1(data38) > 4000){
const err111 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err111];
}
else {
vErrors.push(err111);
}
errors++;
}
}
else {
const err112 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err112];
}
else {
vErrors.push(err112);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data39 = data5.reference_ids;
if(Array.isArray(data39)){
if(data39.length > 20){
const err113 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err113];
}
else {
vErrors.push(err113);
}
errors++;
}
const len3 = data39.length;
for(let i3=0; i3<len3; i3++){
let data40 = data39[i3];
if(typeof data40 === "string"){
if(!(formats0.test(data40))){
const err114 = {instancePath:instancePath+"/content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err114];
}
else {
vErrors.push(err114);
}
errors++;
}
}
else {
const err115 = {instancePath:instancePath+"/content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err115];
}
else {
vErrors.push(err115);
}
errors++;
}
}
}
else {
const err116 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err116];
}
else {
vErrors.push(err116);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data41 = data5.model_profile_version_id;
const _errs133 = errors;
let valid26 = false;
const _errs134 = errors;
if(typeof data41 === "string"){
if(!(formats0.test(data41))){
const err117 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err117];
}
else {
vErrors.push(err117);
}
errors++;
}
}
else {
const err118 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err118];
}
else {
vErrors.push(err118);
}
errors++;
}
var _valid9 = _errs134 === errors;
valid26 = valid26 || _valid9;
const _errs136 = errors;
if(data41 !== null){
const err119 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err119];
}
else {
vErrors.push(err119);
}
errors++;
}
var _valid9 = _errs136 === errors;
valid26 = valid26 || _valid9;
if(!valid26){
const err120 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err120];
}
else {
vErrors.push(err120);
}
errors++;
}
else {
errors = _errs133;
if(vErrors !== null){
if(_errs133){
vErrors.length = _errs133;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data42 = data5.runtime_profile_version_id;
const _errs139 = errors;
let valid27 = false;
const _errs140 = errors;
if(typeof data42 === "string"){
if(!(formats0.test(data42))){
const err121 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err121];
}
else {
vErrors.push(err121);
}
errors++;
}
}
else {
const err122 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err122];
}
else {
vErrors.push(err122);
}
errors++;
}
var _valid10 = _errs140 === errors;
valid27 = valid27 || _valid10;
const _errs142 = errors;
if(data42 !== null){
const err123 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err123];
}
else {
vErrors.push(err123);
}
errors++;
}
var _valid10 = _errs142 === errors;
valid27 = valid27 || _valid10;
if(!valid27){
const err124 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err124];
}
else {
vErrors.push(err124);
}
errors++;
}
else {
errors = _errs139;
if(vErrors !== null){
if(_errs139){
vErrors.length = _errs139;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data43 = data5.budget_usd;
const _errs145 = errors;
const _errs146 = errors;
if(!(((((((data43 === "0") || (data43 === "0.0")) || (data43 === "0.00")) || (data43 === "0.000")) || (data43 === "0.0000")) || (data43 === "0.00000")) || (data43 === "0.000000"))){
const err125 = {};
if(vErrors === null){
vErrors = [err125];
}
else {
vErrors.push(err125);
}
errors++;
}
var valid28 = _errs146 === errors;
if(valid28){
const err126 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err126];
}
else {
vErrors.push(err126);
}
errors++;
}
else {
errors = _errs145;
if(vErrors !== null){
if(_errs145){
vErrors.length = _errs145;
}
else {
vErrors = null;
}
}
}
const _errs147 = errors;
let valid29 = false;
const _errs148 = errors;
if(typeof data43 === "string"){
if(!pattern9.test(data43)){
const err127 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err127];
}
else {
vErrors.push(err127);
}
errors++;
}
}
else {
const err128 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err128];
}
else {
vErrors.push(err128);
}
errors++;
}
var _valid11 = _errs148 === errors;
valid29 = valid29 || _valid11;
const _errs150 = errors;
if(data43 !== null){
const err129 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err129];
}
else {
vErrors.push(err129);
}
errors++;
}
var _valid11 = _errs150 === errors;
valid29 = valid29 || _valid11;
if(!valid29){
const err130 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err130];
}
else {
vErrors.push(err130);
}
errors++;
}
else {
errors = _errs147;
if(vErrors !== null){
if(_errs147){
vErrors.length = _errs147;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data44 = data5.scenario;
if(typeof data44 !== "string"){
const err131 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err131];
}
else {
vErrors.push(err131);
}
errors++;
}
if("comprehensive" !== data44){
const err132 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "comprehensive"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err132];
}
else {
vErrors.push(err132);
}
errors++;
}
}
if(data5.assets !== undefined){
let data45 = data5.assets;
if(Array.isArray(data45)){
if(data45.length > 100){
const err133 = {instancePath:instancePath+"/content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err133];
}
else {
vErrors.push(err133);
}
errors++;
}
const len4 = data45.length;
for(let i4=0; i4<len4; i4++){
let data46 = data45[i4];
if(typeof data46 === "string"){
if(func1(data46) > 2048){
const err134 = {instancePath:instancePath+"/content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err134];
}
else {
vErrors.push(err134);
}
errors++;
}
}
else {
const err135 = {instancePath:instancePath+"/content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err135];
}
else {
vErrors.push(err135);
}
errors++;
}
}
}
else {
const err136 = {instancePath:instancePath+"/content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err136];
}
else {
vErrors.push(err136);
}
errors++;
}
}
if(data5.access_notes !== undefined){
let data47 = data5.access_notes;
if(typeof data47 === "string"){
if(func1(data47) > 4000){
const err137 = {instancePath:instancePath+"/content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err137];
}
else {
vErrors.push(err137);
}
errors++;
}
}
else {
const err138 = {instancePath:instancePath+"/content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err138];
}
else {
vErrors.push(err138);
}
errors++;
}
}
}
else {
const err139 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err139];
}
else {
vErrors.push(err139);
}
errors++;
}
var _valid0 = _errs114 === errors;
if(_valid0 && valid1){
valid1 = false;
passing0 = [passing0, 2];
}
else {
if(_valid0){
valid1 = true;
passing0 = 2;
if(props0 !== true){
props0 = true;
}
}
const _errs160 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err140 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err140];
}
else {
vErrors.push(err140);
}
errors++;
}
for(const key4 in data5){
if(!(func22.call(schema66.properties, key4))){
const err141 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key4},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err141];
}
else {
vErrors.push(err141);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data48 = data5.schema_version;
if(typeof data48 !== "string"){
const err142 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err142];
}
else {
vErrors.push(err142);
}
errors++;
}
if("1.0" !== data48){
const err143 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err143];
}
else {
vErrors.push(err143);
}
errors++;
}
}
if(data5.name !== undefined){
let data49 = data5.name;
if(typeof data49 === "string"){
if(func1(data49) > 120){
const err144 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err144];
}
else {
vErrors.push(err144);
}
errors++;
}
}
else {
const err145 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err145];
}
else {
vErrors.push(err145);
}
errors++;
}
}
if(data5.objective !== undefined){
let data50 = data5.objective;
if(typeof data50 === "string"){
if(func1(data50) > 8000){
const err146 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err146];
}
else {
vErrors.push(err146);
}
errors++;
}
}
else {
const err147 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err147];
}
else {
vErrors.push(err147);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data51 = data5.starting_point;
if(typeof data51 === "string"){
if(func1(data51) > 8000){
const err148 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err148];
}
else {
vErrors.push(err148);
}
errors++;
}
}
else {
const err149 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err149];
}
else {
vErrors.push(err149);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data52 = data5.constraints;
if(typeof data52 === "string"){
if(func1(data52) > 4000){
const err150 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err150];
}
else {
vErrors.push(err150);
}
errors++;
}
}
else {
const err151 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err151];
}
else {
vErrors.push(err151);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data53 = data5.reference_ids;
if(Array.isArray(data53)){
if(data53.length > 20){
const err152 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err152];
}
else {
vErrors.push(err152);
}
errors++;
}
const len5 = data53.length;
for(let i5=0; i5<len5; i5++){
let data54 = data53[i5];
if(typeof data54 === "string"){
if(!(formats0.test(data54))){
const err153 = {instancePath:instancePath+"/content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err153];
}
else {
vErrors.push(err153);
}
errors++;
}
}
else {
const err154 = {instancePath:instancePath+"/content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err154];
}
else {
vErrors.push(err154);
}
errors++;
}
}
}
else {
const err155 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err155];
}
else {
vErrors.push(err155);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data55 = data5.model_profile_version_id;
const _errs179 = errors;
let valid36 = false;
const _errs180 = errors;
if(typeof data55 === "string"){
if(!(formats0.test(data55))){
const err156 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err156];
}
else {
vErrors.push(err156);
}
errors++;
}
}
else {
const err157 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err157];
}
else {
vErrors.push(err157);
}
errors++;
}
var _valid12 = _errs180 === errors;
valid36 = valid36 || _valid12;
const _errs182 = errors;
if(data55 !== null){
const err158 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err158];
}
else {
vErrors.push(err158);
}
errors++;
}
var _valid12 = _errs182 === errors;
valid36 = valid36 || _valid12;
if(!valid36){
const err159 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err159];
}
else {
vErrors.push(err159);
}
errors++;
}
else {
errors = _errs179;
if(vErrors !== null){
if(_errs179){
vErrors.length = _errs179;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data56 = data5.runtime_profile_version_id;
const _errs185 = errors;
let valid37 = false;
const _errs186 = errors;
if(typeof data56 === "string"){
if(!(formats0.test(data56))){
const err160 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err160];
}
else {
vErrors.push(err160);
}
errors++;
}
}
else {
const err161 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err161];
}
else {
vErrors.push(err161);
}
errors++;
}
var _valid13 = _errs186 === errors;
valid37 = valid37 || _valid13;
const _errs188 = errors;
if(data56 !== null){
const err162 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err162];
}
else {
vErrors.push(err162);
}
errors++;
}
var _valid13 = _errs188 === errors;
valid37 = valid37 || _valid13;
if(!valid37){
const err163 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err163];
}
else {
vErrors.push(err163);
}
errors++;
}
else {
errors = _errs185;
if(vErrors !== null){
if(_errs185){
vErrors.length = _errs185;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data57 = data5.budget_usd;
const _errs191 = errors;
const _errs192 = errors;
if(!(((((((data57 === "0") || (data57 === "0.0")) || (data57 === "0.00")) || (data57 === "0.000")) || (data57 === "0.0000")) || (data57 === "0.00000")) || (data57 === "0.000000"))){
const err164 = {};
if(vErrors === null){
vErrors = [err164];
}
else {
vErrors.push(err164);
}
errors++;
}
var valid38 = _errs192 === errors;
if(valid38){
const err165 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err165];
}
else {
vErrors.push(err165);
}
errors++;
}
else {
errors = _errs191;
if(vErrors !== null){
if(_errs191){
vErrors.length = _errs191;
}
else {
vErrors = null;
}
}
}
const _errs193 = errors;
let valid39 = false;
const _errs194 = errors;
if(typeof data57 === "string"){
if(!pattern9.test(data57)){
const err166 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err166];
}
else {
vErrors.push(err166);
}
errors++;
}
}
else {
const err167 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err167];
}
else {
vErrors.push(err167);
}
errors++;
}
var _valid14 = _errs194 === errors;
valid39 = valid39 || _valid14;
const _errs196 = errors;
if(data57 !== null){
const err168 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err168];
}
else {
vErrors.push(err168);
}
errors++;
}
var _valid14 = _errs196 === errors;
valid39 = valid39 || _valid14;
if(!valid39){
const err169 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err169];
}
else {
vErrors.push(err169);
}
errors++;
}
else {
errors = _errs193;
if(vErrors !== null){
if(_errs193){
vErrors.length = _errs193;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data58 = data5.scenario;
if(typeof data58 !== "string"){
const err170 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err170];
}
else {
vErrors.push(err170);
}
errors++;
}
if("exercise" !== data58){
const err171 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "exercise"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err171];
}
else {
vErrors.push(err171);
}
errors++;
}
}
if(data5.organization_name !== undefined){
let data59 = data5.organization_name;
if(typeof data59 === "string"){
if(func1(data59) > 255){
const err172 = {instancePath:instancePath+"/content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err172];
}
else {
vErrors.push(err172);
}
errors++;
}
}
else {
const err173 = {instancePath:instancePath+"/content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err173];
}
else {
vErrors.push(err173);
}
errors++;
}
}
if(data5.known_domains !== undefined){
let data60 = data5.known_domains;
if(Array.isArray(data60)){
if(data60.length > 100){
const err174 = {instancePath:instancePath+"/content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err174];
}
else {
vErrors.push(err174);
}
errors++;
}
const len6 = data60.length;
for(let i6=0; i6<len6; i6++){
let data61 = data60[i6];
if(typeof data61 === "string"){
if(func1(data61) > 253){
const err175 = {instancePath:instancePath+"/content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err175];
}
else {
vErrors.push(err175);
}
errors++;
}
}
else {
const err176 = {instancePath:instancePath+"/content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err176];
}
else {
vErrors.push(err176);
}
errors++;
}
}
}
else {
const err177 = {instancePath:instancePath+"/content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err177];
}
else {
vErrors.push(err177);
}
errors++;
}
}
}
else {
const err178 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err178];
}
else {
vErrors.push(err178);
}
errors++;
}
var _valid0 = _errs160 === errors;
if(_valid0 && valid1){
valid1 = false;
passing0 = [passing0, 3];
}
else {
if(_valid0){
valid1 = true;
passing0 = 3;
if(props0 !== true){
props0 = true;
}
}
const _errs206 = errors;
const _errs209 = errors;
const _errs210 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
let missing0;
if(((data5.repository_url === undefined) && (missing0 = "repository_url")) || ((data5.source_reference_id === undefined) && (missing0 = "source_reference_id"))){
const err179 = {};
if(vErrors === null){
vErrors = [err179];
}
else {
vErrors.push(err179);
}
errors++;
}
else {
if(data5.repository_url !== undefined){
const _errs211 = errors;
if(typeof data5.repository_url !== "string"){
const err180 = {};
if(vErrors === null){
vErrors = [err180];
}
else {
vErrors.push(err180);
}
errors++;
}
var valid44 = _errs211 === errors;
}
else {
var valid44 = true;
}
if(valid44){
if(data5.source_reference_id !== undefined){
const _errs213 = errors;
if(typeof data5.source_reference_id !== "string"){
const err181 = {};
if(vErrors === null){
vErrors = [err181];
}
else {
vErrors.push(err181);
}
errors++;
}
var valid44 = _errs213 === errors;
}
else {
var valid44 = true;
}
}
}
}
var valid43 = _errs210 === errors;
if(valid43){
const err182 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err182];
}
else {
vErrors.push(err182);
}
errors++;
}
else {
errors = _errs209;
if(vErrors !== null){
if(_errs209){
vErrors.length = _errs209;
}
else {
vErrors = null;
}
}
}
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err183 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err183];
}
else {
vErrors.push(err183);
}
errors++;
}
for(const key5 in data5){
if(!(func22.call(schema67.properties, key5))){
const err184 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key5},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err184];
}
else {
vErrors.push(err184);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data64 = data5.schema_version;
if(typeof data64 !== "string"){
const err185 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err185];
}
else {
vErrors.push(err185);
}
errors++;
}
if("1.0" !== data64){
const err186 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err186];
}
else {
vErrors.push(err186);
}
errors++;
}
}
if(data5.name !== undefined){
let data65 = data5.name;
if(typeof data65 === "string"){
if(func1(data65) > 120){
const err187 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err187];
}
else {
vErrors.push(err187);
}
errors++;
}
}
else {
const err188 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err188];
}
else {
vErrors.push(err188);
}
errors++;
}
}
if(data5.objective !== undefined){
let data66 = data5.objective;
if(typeof data66 === "string"){
if(func1(data66) > 8000){
const err189 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err189];
}
else {
vErrors.push(err189);
}
errors++;
}
}
else {
const err190 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err190];
}
else {
vErrors.push(err190);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data67 = data5.starting_point;
if(typeof data67 === "string"){
if(func1(data67) > 8000){
const err191 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err191];
}
else {
vErrors.push(err191);
}
errors++;
}
}
else {
const err192 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err192];
}
else {
vErrors.push(err192);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data68 = data5.constraints;
if(typeof data68 === "string"){
if(func1(data68) > 4000){
const err193 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err193];
}
else {
vErrors.push(err193);
}
errors++;
}
}
else {
const err194 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err194];
}
else {
vErrors.push(err194);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data69 = data5.reference_ids;
if(Array.isArray(data69)){
if(data69.length > 20){
const err195 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err195];
}
else {
vErrors.push(err195);
}
errors++;
}
const len7 = data69.length;
for(let i7=0; i7<len7; i7++){
let data70 = data69[i7];
if(typeof data70 === "string"){
if(!(formats0.test(data70))){
const err196 = {instancePath:instancePath+"/content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err196];
}
else {
vErrors.push(err196);
}
errors++;
}
}
else {
const err197 = {instancePath:instancePath+"/content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err197];
}
else {
vErrors.push(err197);
}
errors++;
}
}
}
else {
const err198 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err198];
}
else {
vErrors.push(err198);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data71 = data5.model_profile_version_id;
const _errs231 = errors;
let valid48 = false;
const _errs232 = errors;
if(typeof data71 === "string"){
if(!(formats0.test(data71))){
const err199 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err199];
}
else {
vErrors.push(err199);
}
errors++;
}
}
else {
const err200 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err200];
}
else {
vErrors.push(err200);
}
errors++;
}
var _valid15 = _errs232 === errors;
valid48 = valid48 || _valid15;
const _errs234 = errors;
if(data71 !== null){
const err201 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err201];
}
else {
vErrors.push(err201);
}
errors++;
}
var _valid15 = _errs234 === errors;
valid48 = valid48 || _valid15;
if(!valid48){
const err202 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err202];
}
else {
vErrors.push(err202);
}
errors++;
}
else {
errors = _errs231;
if(vErrors !== null){
if(_errs231){
vErrors.length = _errs231;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data72 = data5.runtime_profile_version_id;
const _errs237 = errors;
let valid49 = false;
const _errs238 = errors;
if(typeof data72 === "string"){
if(!(formats0.test(data72))){
const err203 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err203];
}
else {
vErrors.push(err203);
}
errors++;
}
}
else {
const err204 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err204];
}
else {
vErrors.push(err204);
}
errors++;
}
var _valid16 = _errs238 === errors;
valid49 = valid49 || _valid16;
const _errs240 = errors;
if(data72 !== null){
const err205 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err205];
}
else {
vErrors.push(err205);
}
errors++;
}
var _valid16 = _errs240 === errors;
valid49 = valid49 || _valid16;
if(!valid49){
const err206 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err206];
}
else {
vErrors.push(err206);
}
errors++;
}
else {
errors = _errs237;
if(vErrors !== null){
if(_errs237){
vErrors.length = _errs237;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data73 = data5.budget_usd;
const _errs243 = errors;
const _errs244 = errors;
if(!(((((((data73 === "0") || (data73 === "0.0")) || (data73 === "0.00")) || (data73 === "0.000")) || (data73 === "0.0000")) || (data73 === "0.00000")) || (data73 === "0.000000"))){
const err207 = {};
if(vErrors === null){
vErrors = [err207];
}
else {
vErrors.push(err207);
}
errors++;
}
var valid50 = _errs244 === errors;
if(valid50){
const err208 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err208];
}
else {
vErrors.push(err208);
}
errors++;
}
else {
errors = _errs243;
if(vErrors !== null){
if(_errs243){
vErrors.length = _errs243;
}
else {
vErrors = null;
}
}
}
const _errs245 = errors;
let valid51 = false;
const _errs246 = errors;
if(typeof data73 === "string"){
if(!pattern9.test(data73)){
const err209 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err209];
}
else {
vErrors.push(err209);
}
errors++;
}
}
else {
const err210 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err210];
}
else {
vErrors.push(err210);
}
errors++;
}
var _valid17 = _errs246 === errors;
valid51 = valid51 || _valid17;
const _errs248 = errors;
if(data73 !== null){
const err211 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err211];
}
else {
vErrors.push(err211);
}
errors++;
}
var _valid17 = _errs248 === errors;
valid51 = valid51 || _valid17;
if(!valid51){
const err212 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err212];
}
else {
vErrors.push(err212);
}
errors++;
}
else {
errors = _errs245;
if(vErrors !== null){
if(_errs245){
vErrors.length = _errs245;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data74 = data5.scenario;
if(typeof data74 !== "string"){
const err213 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err213];
}
else {
vErrors.push(err213);
}
errors++;
}
if("code_audit" !== data74){
const err214 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "code_audit"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err214];
}
else {
vErrors.push(err214);
}
errors++;
}
}
if(data5.repository_url !== undefined){
let data75 = data5.repository_url;
const _errs253 = errors;
let valid52 = false;
const _errs254 = errors;
if(typeof data75 === "string"){
if(func1(data75) > 2048){
const err215 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err215];
}
else {
vErrors.push(err215);
}
errors++;
}
}
else {
const err216 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err216];
}
else {
vErrors.push(err216);
}
errors++;
}
var _valid18 = _errs254 === errors;
valid52 = valid52 || _valid18;
const _errs256 = errors;
if(data75 !== null){
const err217 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err217];
}
else {
vErrors.push(err217);
}
errors++;
}
var _valid18 = _errs256 === errors;
valid52 = valid52 || _valid18;
if(!valid52){
const err218 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err218];
}
else {
vErrors.push(err218);
}
errors++;
}
else {
errors = _errs253;
if(vErrors !== null){
if(_errs253){
vErrors.length = _errs253;
}
else {
vErrors = null;
}
}
}
}
if(data5.source_reference_id !== undefined){
let data76 = data5.source_reference_id;
const _errs259 = errors;
let valid53 = false;
const _errs260 = errors;
if(typeof data76 === "string"){
if(!(formats0.test(data76))){
const err219 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err219];
}
else {
vErrors.push(err219);
}
errors++;
}
}
else {
const err220 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err220];
}
else {
vErrors.push(err220);
}
errors++;
}
var _valid19 = _errs260 === errors;
valid53 = valid53 || _valid19;
const _errs262 = errors;
if(data76 !== null){
const err221 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err221];
}
else {
vErrors.push(err221);
}
errors++;
}
var _valid19 = _errs262 === errors;
valid53 = valid53 || _valid19;
if(!valid53){
const err222 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err222];
}
else {
vErrors.push(err222);
}
errors++;
}
else {
errors = _errs259;
if(vErrors !== null){
if(_errs259){
vErrors.length = _errs259;
}
else {
vErrors = null;
}
}
}
}
if(data5.revision !== undefined){
let data77 = data5.revision;
const _errs265 = errors;
let valid54 = false;
const _errs266 = errors;
if(typeof data77 === "string"){
if(func1(data77) > 255){
const err223 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err223];
}
else {
vErrors.push(err223);
}
errors++;
}
}
else {
const err224 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err224];
}
else {
vErrors.push(err224);
}
errors++;
}
var _valid20 = _errs266 === errors;
valid54 = valid54 || _valid20;
const _errs268 = errors;
if(data77 !== null){
const err225 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err225];
}
else {
vErrors.push(err225);
}
errors++;
}
var _valid20 = _errs268 === errors;
valid54 = valid54 || _valid20;
if(!valid54){
const err226 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err226];
}
else {
vErrors.push(err226);
}
errors++;
}
else {
errors = _errs265;
if(vErrors !== null){
if(_errs265){
vErrors.length = _errs265;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err227 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err227];
}
else {
vErrors.push(err227);
}
errors++;
}
var _valid0 = _errs206 === errors;
if(_valid0 && valid1){
valid1 = false;
passing0 = [passing0, 4];
}
else {
if(_valid0){
valid1 = true;
passing0 = 4;
if(props0 !== true){
props0 = true;
}
}
}
}
}
}
if(!valid1){
const err228 = {instancePath:instancePath+"/content",schemaPath:"#/properties/content/oneOf",keyword:"oneOf",params:{passingSchemas: passing0},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err228];
}
else {
vErrors.push(err228);
}
errors++;
}
else {
errors = _errs13;
if(vErrors !== null){
if(_errs13){
vErrors.length = _errs13;
}
else {
vErrors = null;
}
}
}
}
if(data.created_at !== undefined){
let data78 = data.created_at;
if(typeof data78 === "string"){
if(!(formats2.validate(data78))){
const err229 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err229];
}
else {
vErrors.push(err229);
}
errors++;
}
}
else {
const err230 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err230];
}
else {
vErrors.push(err230);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data79 = data.updated_at;
if(typeof data79 === "string"){
if(!(formats2.validate(data79))){
const err231 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err231];
}
else {
vErrors.push(err231);
}
errors++;
}
}
else {
const err232 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err232];
}
else {
vErrors.push(err232);
}
errors++;
}
}
}
else {
const err233 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err233];
}
else {
vErrors.push(err233);
}
errors++;
}
validate45.errors = vErrors;
return errors === 0;
}
validate45.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateSavedTaskDraftPage = validate46;
const schema68 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/SavedTaskDraft"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"maxLength":512,"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"TaskDraftPageResponse","type":"object"};

function validate46(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate46.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate45(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate45.errors : vErrors.concat(validate45.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
const _errs6 = errors;
let valid3 = false;
const _errs7 = errors;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
else {
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
var _valid0 = _errs7 === errors;
valid3 = valid3 || _valid0;
const _errs9 = errors;
if(data2 !== null){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid0 = _errs9 === errors;
valid3 = valid3 || _valid0;
if(!valid3){
const err8 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
else {
errors = _errs6;
if(vErrors !== null){
if(_errs6){
vErrors.length = _errs6;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err9 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
validate46.errors = vErrors;
return errors === 0;
}
validate46.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateError = validate48;
const schema69 = {"type":"object","additionalProperties":false,"required":["code","message","trace_id"],"properties":{"code":{"type":"string","enum":["UNAUTHENTICATED","FORBIDDEN","NOT_FOUND","VALIDATION_FAILED","SCOPE_DENIED","PREVIEW_EXPIRED","VERSION_CONFLICT","IDEMPOTENCY_CONFLICT","INVALID_TRANSITION","RATE_LIMITED","SERVICE_UNAVAILABLE","CURSOR_EXPIRED","INTERNAL_ERROR"]},"message":{"type":"string","minLength":1,"maxLength":500},"trace_id":{"type":"string","format":"uuid"},"field_errors":{"type":"array","maxItems":30,"items":{"type":"object","additionalProperties":false,"required":["field","message"],"properties":{"field":{"type":"string","minLength":1,"maxLength":128},"message":{"type":"string","minLength":1,"maxLength":300}}}}}};

function validate48(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate48.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.code === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "code"},message:"must have required property '"+"code"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.message === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.trace_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "trace_id"},message:"must have required property '"+"trace_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
for(const key0 in data){
if(!((((key0 === "code") || (key0 === "message")) || (key0 === "trace_id")) || (key0 === "field_errors"))){
const err3 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
if(data.code !== undefined){
let data0 = data.code;
if(typeof data0 !== "string"){
const err4 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(!(((((((((((((data0 === "UNAUTHENTICATED") || (data0 === "FORBIDDEN")) || (data0 === "NOT_FOUND")) || (data0 === "VALIDATION_FAILED")) || (data0 === "SCOPE_DENIED")) || (data0 === "PREVIEW_EXPIRED")) || (data0 === "VERSION_CONFLICT")) || (data0 === "IDEMPOTENCY_CONFLICT")) || (data0 === "INVALID_TRANSITION")) || (data0 === "RATE_LIMITED")) || (data0 === "SERVICE_UNAVAILABLE")) || (data0 === "CURSOR_EXPIRED")) || (data0 === "INTERNAL_ERROR"))){
const err5 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/enum",keyword:"enum",params:{allowedValues: schema69.properties.code.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.message !== undefined){
let data1 = data.message;
if(typeof data1 === "string"){
if(func1(data1) > 500){
const err6 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/maxLength",keyword:"maxLength",params:{limit: 500},message:"must NOT have more than 500 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data1) < 1){
const err7 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
else {
const err8 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.trace_id !== undefined){
let data2 = data.trace_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err9 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
else {
const err10 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.field_errors !== undefined){
let data3 = data.field_errors;
if(Array.isArray(data3)){
if(data3.length > 30){
const err11 = {instancePath:instancePath+"/field_errors",schemaPath:"#/properties/field_errors/maxItems",keyword:"maxItems",params:{limit: 30},message:"must NOT have more than 30 items"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(data4 && typeof data4 == "object" && !Array.isArray(data4)){
if(data4.field === undefined){
const err12 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/required",keyword:"required",params:{missingProperty: "field"},message:"must have required property '"+"field"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data4.message === undefined){
const err13 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
for(const key1 in data4){
if(!((key1 === "field") || (key1 === "message"))){
const err14 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data4.field !== undefined){
let data5 = data4.field;
if(typeof data5 === "string"){
if(func1(data5) > 128){
const err15 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/maxLength",keyword:"maxLength",params:{limit: 128},message:"must NOT have more than 128 characters"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(func1(data5) < 1){
const err16 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
else {
const err17 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data4.message !== undefined){
let data6 = data4.message;
if(typeof data6 === "string"){
if(func1(data6) > 300){
const err18 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/maxLength",keyword:"maxLength",params:{limit: 300},message:"must NOT have more than 300 characters"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(func1(data6) < 1){
const err19 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
else {
const err20 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
}
else {
const err21 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
}
else {
const err22 = {instancePath:instancePath+"/field_errors",schemaPath:"#/properties/field_errors/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
}
else {
const err23 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
validate48.errors = vErrors;
return errors === 0;
}
validate48.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};
