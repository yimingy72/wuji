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
const schema32 = {"type":"object","additionalProperties":false,"required":["user_id","display_name","csrf_token","expires_at","permissions_version"],"properties":{"user_id":{"type":"string","format":"uuid"},"display_name":{"type":"string","minLength":1,"maxLength":100},"csrf_token":{"type":"string","minLength":1,"maxLength":256},"expires_at":{"type":"string","format":"date-time"},"permissions_version":{"$ref":"urn:wuji:contracts:0.2#/$defs/Version"}}};
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
const err16 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.2#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err17 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.2#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.2#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const schema34 = {"type":"object","additionalProperties":false,"required":["id","tenant_id","name","permissions"],"properties":{"id":{"type":"string","format":"uuid"},"tenant_id":{"type":"string","format":"uuid"},"name":{"type":"string","minLength":1,"maxLength":120},"permissions":{"type":"array","maxItems":10,"items":{"$ref":"urn:wuji:contracts:0.2#/$defs/Permission"}}}};
const schema35 = {"type":"string","enum":["project.read","task.read","task.create","task.control","artifact.read","artifact.download_sensitive"]};

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
const err13 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.2#/$defs/Permission/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(!((((((data4 === "project.read") || (data4 === "task.read")) || (data4 === "task.create")) || (data4 === "task.control")) || (data4 === "artifact.read")) || (data4 === "artifact.download_sensitive"))){
const err14 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.2#/$defs/Permission/enum",keyword:"enum",params:{allowedValues: schema35.enum},message:"must be equal to one of the allowed values"};
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
const schema36 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.2#/$defs/Project"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

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

export const validateError = validate25;
const schema37 = {"type":"object","additionalProperties":false,"required":["code","message","trace_id"],"properties":{"code":{"type":"string","enum":["UNAUTHENTICATED","FORBIDDEN","NOT_FOUND","VALIDATION_FAILED","SCOPE_DENIED","PREVIEW_EXPIRED","VERSION_CONFLICT","IDEMPOTENCY_CONFLICT","INVALID_TRANSITION","RATE_LIMITED","SERVICE_UNAVAILABLE","CURSOR_EXPIRED","INTERNAL_ERROR"]},"message":{"type":"string","minLength":1,"maxLength":500},"trace_id":{"type":"string","format":"uuid"},"field_errors":{"type":"array","maxItems":30,"items":{"type":"object","additionalProperties":false,"required":["field","message"],"properties":{"field":{"type":"string","minLength":1,"maxLength":128},"message":{"type":"string","minLength":1,"maxLength":300}}}}}};

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
const err5 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/enum",keyword:"enum",params:{allowedValues: schema37.properties.code.enum},message:"must be equal to one of the allowed values"};
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
validate25.errors = vErrors;
return errors === 0;
}
validate25.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};
